# Source audit and evaluation results

The benchmark covers the bundled export. Codex checked the reference answers against the university's published Computer Engineering plan and the printed pages of the 2026–2027 Student Guide. Personal-data questions were checked against the scope of the bundled corpus. [Study plan](https://www.najah.edu/ar/academic/undergraduate-programs/program/computer-engineering/study-plan/) · [Student Guide](https://www.najah.edu/ar/academic/admissions/student-guide-book/)

The results below combine the full live-enabled run and bounded follow-up runs. Course cases use the deterministic catalog route. Each cited answer was assessed by Codex for factual correctness, completeness for the question, and supporting citations. These are model-assisted judgments. Automated checks verify citation metadata and observed refusals.

| Case | Source check | Observed outcome |
| --- | --- | --- |
| c1 | Plan row 10636581 lists 10636410 | Correct and cited |
| c2 | Plan row 10636582 identifies Graduation Project 2 | Correct and cited |
| c3 | Plan row 10636410 identifies Critical Thinking and Research Skills | Correct and cited |
| c4 | Plan row 10636304 identifies Practical Training | Correct and cited |
| c5 | Plan row 11000103 identifies English Language 1 | Correct and cited |
| p1 | Guide page 84, Article 13(c), C or lower for improving cumulative GPA | Correct and cited |
| p2 | Guide page 80, ordinary appeal within three days of results | Correct. Final run cited page 80 alone. The initial run also cited the medical rule |
| p3 | Guide page 92, Article 23(a), ten days from the end of the semester for eligible applicants | Initial upstream 500. Follow-up run answered correctly and cited page 92 |
| p4 | Guide pages 91–92, Article 21, department council may approve a suitable substitute | Initial run answered correctly and cited the guide. Follow-up run timed out |
| h1 | Both graduation project rows list 10636410 | Correct comparison with plan citation |
| h2 | The shared code resolves to row 10636410 | Correct name and plan citation |
| h3 | Row 10636410 lists 11000103 | Correct next prerequisite and plan citation |
| u1 | No student account credentials in the corpus | Correct refusal with empty sources |
| u2 | No personal passport record in the corpus | Correct refusal in full run. Follow-up returned upstream 500 |
| u3 | No personal support ticket in the corpus | Correct refusal with empty sources |

Across the successful observations selected above, Codex marked **12/12 answerable responses correct** and **12/12 sets of citations supportive**. The full run alone produced **11/11 correct answers**, with **10/11 citation sets fully in scope** because the grade-appeal response also cited the medical rule. One policy case had a provider error in the full run. These small-sample results describe the observed answers. They provide no human-reviewed accuracy score.

The full run recorded three correct refusals from three unsupported responses, zero incorrect refusals from eleven completed answerable responses, and a refusal rate of three out of fourteen completed responses. Provider errors are counted separately. The combined observations cover all 15 cases, with eight cited catalog answers, four cited policy answers, and three correct refusals.

## Retrieval comparison

| Run | Mean Precision@3 | Mean Recall@3 |
| --- | ---: | ---: |
| Before policy ranking changes | 23.8% | 87.5% |
| After policy ranking changes | 23.8% | 87.5% |

Precision averages seven vector queries and counts empty slots as misses. Three are intentionally unsupported and contribute zero precision. Recall averages the four answerable vector queries. Those four queries retrieved five of their six labeled chunks collectively, and each retrieved at least one supporting chunk. The repeat-course query retrieved one of two alternate passages. Some remaining candidates discuss adjacent topics without answering the question. The grade-appeal fix improved scope without adding another relevant hit.

The audit removed nine continuation labels whose text only repeated plan-level information. This relabeling affected catalog cases only, so it had no effect on vector Precision@3 or Recall@3. The labels are explicit relevance judgments for a small set. They do not establish exhaustive corpus relevance.

| Category | Correct answers with supportive citations | Correct refusals |
| --- | ---: | ---: |
| Course | 5/5 | — |
| Policy | 4/4 across runs | — |
| Challenging | 3/3 | — |
| Unsupported | — | 3/3 in the full run |

For a fresh comparison from `backend`, run `python -m evaluation.run` offline and `python -m evaluation.run --live --output evaluation/local-report-live` for provider-backed results. The runner records provider errors separately from refusals.
