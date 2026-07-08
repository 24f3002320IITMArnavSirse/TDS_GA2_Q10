# FastAPI Middleware Stack Assignment

This service implements `GET /ping` with request ID propagation, scoped CORS, and per-client rate limiting.

## Configuration

Set these environment variables before deployment:

- `EMAIL`: your IITM/login email address. This repository did not contain an existing email value.
- `EXAM_ORIGIN`: optional exam/grader page origin. The assigned origin is always allowed.

Assigned CORS origin:

```text
https://app-3urmir.example.com
```

Rate limit:

```text
14 requests / 10 seconds per X-Client-Id
```

## Run Locally

```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

## Test

```bash
pip install -r requirements-dev.txt
pytest
```

## Deploy

Use any Python ASGI host that can install `requirements.txt` and run:

```bash
uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
```
