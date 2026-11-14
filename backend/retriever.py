import re

from config import TOP_K, MAX_DISTANCE

_POLICY_QUERY = re.compile(
    r"مسموح|يسمح|يجوز|يحق|اعاده|تحسين|الحد|اعتراض|\b(?:allowed|eligible|retake|repeat|maximum|minimum|appeal)\b"
)
_STOP_WORDS = set("ما هي هو هل كم في فيها فيه من على عن عند او و الى هذا ذلك طالب جامعه نجاح دليل".split())
_ALIASES = {
    word: canonical
    for canonical, variants in {
        "اعاده": "اعاد يعيد يعاد اعادته اعادتها تكرار retake repeat",
        "مساق": "مساقات مساقا ماده مواد مقرر مقررات course courses",
        "علامه": "علامات درجه درجات تقدير mark marks grade grades",
        "سماح": "مسموح يسمح يجوز يحق سماح allowed eligible",
    }.items()
    for word in variants.split()
}


def _normalize(text):
    return re.sub(r"[\u064b-\u065fـ]", "", text.casefold()).translate(
        str.maketrans("أإآٱىة", "اااايه")
    )


def _terms(text):
    terms = set()
    for word in re.findall(r"[^\W_]+", _normalize(text)):
        if len(word) > 3:
            word = word.removeprefix("ال")
        if word not in _STOP_WORDS:
            terms.add(_ALIASES.get(word, word))
    return terms


def _promote_policy_match(matches, chunks, question):
    query_terms = _terms(question)
    metadata = {chunk["id"]: chunk.get("metadata") or {} for chunk in chunks}
    scoped = []
    general = []
    out_of_scope = set()
    for match in matches:
        meta = metadata.get(match["id"], {})
        if not isinstance(meta, dict):
            continue
        collection = meta.get("collection")
        overlap = len(query_terms & _terms(match["text"]))
        if collection == "academic_regulations":
            if overlap >= 2:
                general.append((overlap, match))
        program = meta.get("program")
        if collection == "medical_program_regulations":
            program_terms = _terms(program.partition("(")[0]) if isinstance(program, str) else set()
            if program_terms and program_terms <= query_terms:
                if overlap >= 2:
                    scoped.append((overlap, match))
            elif not ({"طب", "طبي", "طبيه", "medicine", "medical", "md", "bbms"} & query_terms):
                out_of_scope.add(match["id"])

    candidates = scoped or general
    if not candidates:
        return matches
    # Stable sorting keeps semantic order when lexical scores tie.
    ranked = [match for _, match in sorted(candidates, key=lambda item: item[0], reverse=True)]
    excluded = {match["id"] for match in ranked} | out_of_scope
    return [*ranked, *(match for match in matches if match["id"] not in excluded)]


def retrieve(store, question, *, k=TOP_K):
    policy_question = _POLICY_QUERY.search(_normalize(question)) is not None
    results = store.search(question, max(k, 12) if policy_question else k)
    ids = results["ids"][0]
    docs = results["documents"][0]
    metas = results["metadatas"][0]
    distances = results["distances"][0]
    matches = [
        {"id": chunk_id, "text": doc, "source": meta["source"], "page": meta["page"], "distance": distance}
        for chunk_id, doc, meta, distance in zip(ids, docs, metas, distances)
    ]
    if MAX_DISTANCE is not None:
        matches = [m for m in matches if m["distance"] <= MAX_DISTANCE]
    if policy_question:
        matches = _promote_policy_match(matches, store.chunks, question)
    return matches[:k]
