# Reviewing evaluation results

Run `python -m evaluation.run` from `backend`. The default files are `evaluation/local-report.json` and `evaluation/local-report.md`. Use `--live` to allow generation. `--case` can be repeated and automatically includes prior turns needed by selected cases.

Each reference answer uses the bundled academic export. The benchmark labels supporting chunk IDs, including alternate excerpts where identified. Reviewers can flag other relevant excerpts for a later revision of the benchmark.

For each cited answer under review:

1. Compare the answer with the reference and check every additional factual claim.
2. Read the selected catalog records or model quotes and their associated excerpts. Check applicability, including program and plan version where relevant.
3. Confirm that the cited source and page correspond to the evidence. Mark citation support false if the excerpt fails to establish a material claim even when the source and page are valid.
4. Explain any failure or unresolved uncertainty in the notes.

```json
{
  "c1": {
    "answer_correct": true,
    "citations_support_answer": true,
    "notes": "Example review entry. Replace with your judgment after reading the report."
  }
}
```

Apply judgments with `python -m evaluation.run --review-report evaluation/local-report.json --reviews reviews.json --output evaluation/local-report-reviewed`. Precision and recall remain automated. The factual and citation accuracy averages cover the submitted human judgments. Cases with a correct refusal and no citations pass the deterministic refusal check. Cited answers remain pending until reviewed. Errors and skipped generation do not count as refusals.
