from evaluation.run import Case, Review, assess, retrieval_metrics, summarize
from config import NO_ANSWER


def test_retrieval_metrics_handle_empty_partial_and_duplicate_results():
    assert retrieval_metrics([], ["a"], 3) == {"precision_at_k": 0, "recall_at_k": 0}
    assert retrieval_metrics(["a", "a", "irrelevant", "b"], ["a", "b"], 3) == {
        "precision_at_k": 1 / 3, "recall_at_k": 0.5,
    }
    assert retrieval_metrics(["a"], [], 3) == {"precision_at_k": 0, "recall_at_k": None}


def test_citation_metadata_and_human_support_are_separate():
    case = Case(id="a", category="course", question="Name?", reference_answer="Course",
                expected_chunk_ids=["a"], should_refuse=False)
    citation = {"source": "guide.pdf", "page": "1"}
    evidence = [{"citation": citation}]
    assert assess(case, {"answer": "Course", "sources": []}, evidence)["status"] == "invalid_citations"
    result = {"answer": "Course", "sources": [citation]}
    assert assess(case, result, evidence)["status"] == "review_pending"
    review = Review(answer_correct=True, citations_support_answer=False, notes="Wrong passage")
    assert assess(case, result, evidence, review)["status"] == "human_review_failed"


def test_refusal_denominators_exclude_provider_failures():
    unsupported = Case(id="u", category="unanswerable", question="Password?", reference_answer=None,
                       expected_chunk_ids=[], should_refuse=True)
    supported = Case(id="s", category="course", question="Name?", reference_answer="Course",
                     expected_chunk_ids=["a"], should_refuse=False)
    refusal = {"answer": NO_ANSWER, "sources": []}
    rows = [
        {**case.model_dump(), **assess(case, result, [])}
        for case, result in [(unsupported, refusal), (supported, refusal), (supported, None)]
    ]
    summary = summarize(rows)
    assert summary["passed"] == 1 and summary["failed"] == 2
    assert summary["refusal_rate"] == summary["correct_refusal_rate"] == summary["incorrect_refusal_rate"] == 1
    assert summary["answered_or_refused"] == 2
    assert summary["human_answer_accuracy"] is None
