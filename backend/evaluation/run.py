"""Run the catalog and retrieval benchmark from backend with python -m evaluation.run."""

import argparse
import hashlib
import json
from pathlib import Path
from statistics import mean
from types import SimpleNamespace
from unittest.mock import patch

from pydantic import BaseModel, Field, TypeAdapter, model_validator

import course_lookup
import rag_pipeline as rag
from citations import source_citation
from config import EMBEDDING_MODEL, MAX_DISTANCE, TOP_K
from conversation import ChatTurn
from data_loader import load_chunks, resolve_page


class Case(BaseModel):
    id: str
    category: str
    question: str
    reference_answer: str | None
    expected_chunk_ids: list[str]
    should_refuse: bool
    history_ids: list[str] = Field(default_factory=list)
    verification_notes: str | None = None

    @model_validator(mode="after")
    def validate_ground_truth(self):
        if self.should_refuse != (not self.expected_chunk_ids and self.reference_answer is None):
            raise ValueError("Refusal cases must have no reference answer or relevant chunks")
        if not self.should_refuse and (not self.reference_answer or not self.expected_chunk_ids):
            raise ValueError("Answerable cases need an answer and relevant chunks")
        return self


def retrieval_metrics(retrieved, relevant, k):
    if k < 1:
        raise ValueError("k must be positive")
    relevant = set(relevant)
    hits = len(set(retrieved[:k]) & relevant)
    return {"precision_at_k": hits / k, "recall_at_k": hits / len(relevant) if relevant else None}


def assess(case, result, evidence, review=None):
    if result is None:
        return {"status": "error", "refused": None, "citation_metadata_valid": None}
    refused = result["answer"] == rag.NO_ANSWER
    available = [item["citation"] for item in evidence]
    sources = result["sources"]
    valid = bool(sources) and all(source in available for source in sources)
    if refused != case.should_refuse:
        status = "incorrect_refusal" if refused else "unexpected_answer"
    elif refused:
        status = "passed" if not sources else "invalid_citations"
    elif not valid:
        status = "invalid_citations"
    elif review is None:
        status = "review_pending"
    elif review.answer_correct and review.citations_support_answer:
        status = "passed"
    else:
        status = "human_review_failed"
    return {"status": status, "refused": refused, "citation_metadata_valid": valid if not refused else None}


class Review(BaseModel):
    answer_correct: bool
    citations_support_answer: bool
    notes: str


def summarize(rows):
    observed = [row for row in rows if row.get("refused") is not None]
    unsupported = [row for row in observed if row["should_refuse"]]
    answerable = [row for row in observed if not row["should_refuse"]]
    reviewed = [row["human_review"] for row in rows if row.get("human_review")]
    return {
        "evaluated": len(rows),
        "passed": sum(row["status"] == "passed" for row in rows),
        "failed": sum(row["status"] not in {"passed", "review_pending", "generation_skipped"} for row in rows),
        "pending": sum(row["status"] in {"review_pending", "generation_skipped"} for row in rows),
        "mean_precision_at_k": _mean(rows, "precision_at_k"),
        "mean_recall_at_k": _mean(rows, "recall_at_k"),
        "refusal_rate": _mean(observed, "refused"),
        "correct_refusal_rate": _mean(unsupported, "refused"),
        "incorrect_refusal_rate": _mean(answerable, "refused"),
        "answered_or_refused": len(observed),
        "unsupported_responses": len(unsupported),
        "answerable_responses": len(answerable),
        "human_reviewed": len(reviewed),
        "human_answer_accuracy": _mean(reviewed, "answer_correct"),
        "human_citation_accuracy": _mean(reviewed, "citations_support_answer"),
    }


def _mean(rows, key):
    values = [row[key] for row in rows if row.get(key) is not None]
    return mean(values) if values else None


class GenerationSkipped(Exception):
    pass


def run(cases, chunks, live):
    by_id = {chunk["id"]: chunk for chunk in chunks}
    reports = {}
    select = course_lookup.select_course
    retrieve = rag.retrieve
    verify = rag.cited_sources
    exact_answer = rag.exact_course_answer
    for case in cases:
        history = []
        for previous_id in case.history_ids:
            previous = reports[previous_id]
            if not previous["result"] or not previous["result"]["sources"]:
                break
            history.extend([
                ChatTurn(role="user", content=previous["question"]),
                ChatTurn(role="assistant", content=previous["result"]["answer"]),
            ])
        evidence = []
        retrieved_ids = []
        searched = False
        quotes = []
        skipped = False

        def capture(chunk, *, distance=None):
            evidence.append({
                "id": chunk["id"], "text": chunk["text"], "distance": distance,
                "citation": source_citation(chunk["source"], resolve_page(chunk)),
            })

        def catalog(question, code, candidates):
            selected = select(question, code, candidates)
            if selected:
                capture(selected[0])
            return selected

        def exact(*args, **kwargs):
            with patch.object(course_lookup, "select_course", side_effect=catalog):
                return exact_answer(*args, **kwargs)

        def vector_search(*args, **kwargs):
            nonlocal searched
            searched = True
            matches = retrieve(*args, **kwargs)
            for match in matches:
                retrieved_ids.append(match["id"])
                capture(by_id[match["id"]], distance=match["distance"])
            return matches

        def citation_check(items, matches):
            result = verify(items, matches)
            quotes.extend(item.model_dump() for item in items)
            return result

        def skip_generation(**kwargs):
            nonlocal skipped
            skipped = True
            raise GenerationSkipped()

        result = None
        reason = None
        if len(history) != 2 * len(case.history_ids):
            reason = "A required prior turn did not return a cited answer"
        else:
            with patch.object(rag, "exact_course_answer", side_effect=exact), patch.object(
                rag, "retrieve", side_effect=vector_search
            ), patch.object(rag, "cited_sources", side_effect=citation_check):
                try:
                    if live:
                        result = rag.ask_rag(case.question, history)
                    else:
                        client = SimpleNamespace(models=SimpleNamespace(generate_content=skip_generation))
                        with patch.object(rag, "_client", client):
                            result = rag.ask_rag(case.question, history)
                except rag.RagUnavailable as error:
                    reason = "Gemini disabled in offline mode" if skipped else error.category

        row = {
            **case.model_dump(), "result": result, "evidence": evidence, "model_evidence": quotes,
            "expected_sources": [{
                "id": chunk_id,
                "citation": source_citation(by_id[chunk_id]["source"], resolve_page(by_id[chunk_id])),
            } for chunk_id in case.expected_chunk_ids],
            "failure_reason": reason,
            "route": "vector" if searched else "catalog" if evidence else "no_candidates",
            **assess(case, result, evidence),
        }
        if skipped:
            row["status"] = "generation_skipped"
        if searched:
            row.update(retrieval_metrics(retrieved_ids, case.expected_chunk_ids, TOP_K))
        if row["failure_reason"] is None and row["status"] != "passed":
            row["failure_reason"] = row["status"]
        reports[case.id] = row
    return list(reports.values())


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Triple Spark evaluation", "", f"Mode: {report['mode']}", ""]
    for name, summary in [("Overall", report["summary"]), *report["categories"].items()]:
        lines.extend([f"## {name}", "", *[f"- {key}: {value}" for key, value in summary.items()], ""])
    lines.extend(["## Cases", ""])
    for row in report["cases"]:
        lines.extend([
            f"### {row['id']} · {row['status']}", "", row["question"], "",
            f"- Reference: {row['reference_answer']}",
            f"- Source verification: {row.get('verification_notes') or 'not recorded'}",
            f"- Result: {row['result']}",
            f"- Evidence IDs: {', '.join(item['id'] for item in row['evidence']) or 'none'}",
            f"- Reason: {row['failure_reason'] or 'none'}", "",
        ])
    path.with_suffix(".md").write_text("\n".join(lines), encoding="utf-8")


def report_for(rows, **metadata):
    return {
        **metadata, "cases": rows, "summary": summarize(rows),
        "categories": {
            category: summarize([row for row in rows if row["category"] == category])
            for category in sorted({row["category"] for row in rows})
        },
    }


def main():
    directory = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Allow Gemini generation")
    parser.add_argument("--case", action="append", help="Evaluate selected IDs plus their history")
    parser.add_argument("--output", type=Path, default=Path("evaluation/local-report"))
    parser.add_argument("--review-report", type=Path, help="Apply human review to an existing JSON report")
    parser.add_argument("--reviews", type=Path, help="JSON mapping case IDs to Review fields")
    args = parser.parse_args()
    if bool(args.review_report) != bool(args.reviews):
        parser.error("--review-report and --reviews must be supplied together")
    if args.review_report:
        report = json.loads(args.review_report.read_bytes())
        rows = report["cases"]
        reviews = TypeAdapter(dict[str, Review]).validate_json(args.reviews.read_bytes(), strict=True)
        eligible = {row["id"] for row in rows if row.get("citation_metadata_valid")}
        if not reviews.keys() <= eligible:
            parser.error("Review IDs must refer to cited answers in the input report")
        for row in rows:
            review = reviews.get(row["id"])
            if review:
                row.update(assess(Case.model_validate(row), row["result"], row["evidence"], review))
                row["human_review"] = review.model_dump()
                row["failure_reason"] = None if row["status"] == "passed" else review.notes
        report.update(report_for(rows))
    else:
        from embeddings_store import VectorStore

        cases = TypeAdapter(list[Case]).validate_json((directory / "cases.json").read_bytes(), strict=True)
        data_path = directory.parent / "data" / "chunks.json"
        chunks = load_chunks(data_path)
        ids = {chunk["id"] for chunk in chunks}
        seen = set()
        for case in cases:
            if case.id in seen or not set(case.history_ids) <= seen or not set(case.expected_chunk_ids) <= ids:
                parser.error(f"Invalid case ID, history, or chunk labels for {case.id}")
            seen.add(case.id)
        selected = set(args.case or seen)
        if not selected <= seen:
            parser.error("Unknown --case value")
        for case in reversed(cases):
            if case.id in selected:
                selected.update(case.history_ids)
        store = VectorStore(chunks)
        with patch.object(rag, "_store", store):
            rows = run([case for case in cases if case.id in selected], chunks, args.live)
        report = report_for(
            rows, mode="live" if args.live else "offline", top_k=TOP_K,
            max_distance=MAX_DISTANCE, embedding_model=EMBEDDING_MODEL,
            gemini_model=rag.GEMINI_MODEL if args.live else None,
            dataset_sha256=hashlib.sha256(data_path.read_bytes()).hexdigest(),
        )
    write_report(args.output, report)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
