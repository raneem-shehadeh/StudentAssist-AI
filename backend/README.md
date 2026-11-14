# StudentAssist-AI backend

FastAPI serves course catalog lookups and source-grounded academic questions. See the [project README](../README.md) for setup, tests, the retrieval architecture, and evaluation commands.

## Dataset contract

`DATA_PATH` defaults to `data/chunks.json`. Relative paths resolve from this directory. The input is a nonempty UTF-8 JSON array of objects. Each chunk needs a unique nonblank string `id`, nonblank strings `text` and `source`, and a nonnegative integer `chunk_index`. The optional `page` accepts a positive integer or a nonblank page label. The loader preserves additional metadata, including course records and source references.

The repository consumes prepared chunks. Restart the backend after replacing the dataset so the next request builds a fresh index. To validate the dataset without loading embeddings, run this command from the backend directory.

```sh
python -c "from data_loader import load_chunks; print(len(load_chunks('data/chunks.json')))"
```

## API contract

`GET /` reports process liveness. Send JSON to `POST /api/ask` with a string `question` and optionally up to eight recent `history` messages. Each message has a `role` of `user` or `assistant` and `content` of at most 1,000 characters.

```json
{"question":"ما المتطلب السابق لمساق 10636581؟"}
```

```json
{"answer":"اسم المساق 10636581: مشروع تخرج 1\nالمتطلبات السابقة: 10636410","sources":[{"source":"https://www.najah.edu/ar/academic/undergraduate-programs/program/computer-engineering/study-plan/","page":"Unknown"}]}
```

| Condition | Status | Response |
| --- | --- | --- |
| Supported answer | 200 | Answer and citation metadata |
| Insufficient evidence | 200 | Arabic refusal with empty sources |
| Whitespace-only question | 200 | Request to enter a question with empty sources |
| Invalid request body | 422 | Validation details |
| Dataset or initialization error | 500 | Safe error detail |
| Provider rate limit, failure, or timeout | 429, 502, 503, or 504 | Safe error detail |

Page values are strings in responses. Quote validation checks that evidence occurs in the referenced excerpt. Assess factual support by comparing the answer with that excerpt.

For a browser that calls FastAPI directly, include its origin in `FRONTEND_ORIGINS`. Store server credentials in the process environment or a local `.env` file. CORS controls browser access and provides no authentication.

## Evaluation

Run `python -m evaluation.run` for the bundled benchmark or `python evaluate_retrieval.py --help` for custom retrieval labels. The [evaluation guide](evaluation/README.md) explains how to review outputs. Set a distance cutoff only after calibrating on labeled questions and checking recall on a separate set.

## Development tools

Codex assisted with backend implementation, testing, and documentation. Gemini supplies structured answers at runtime.
