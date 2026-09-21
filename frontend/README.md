# Sift &mdash; CV Review Frontend

React + Vite + TypeScript + Tailwind CSS + React Router frontend for the HR CV
review application.

## Getting started

```bash
cd frontend
cp .env.example .env      # edit VITE_API_BASE_URL if your API isn't on :8004
npm install
npm run dev
```

The app expects the backend described in `../UNCOMPLETED_BACKEND.md` (or the
equivalent tracked gaps). See **Backend integration status** below for what
works today versus what's stubbed.

## Routes

| Path      | Page                                    |
| --------- | ---------------------------------------- |
| `/`       | Team & product introduction              |
| `/setup`  | Job requirements + CV upload             |
| `/review` | Processed CV review workspace            |
| `/cvs`    | All CVs (search, filter, paginate)       |

## Project structure

```text
src/
|-- api/            typed API client + one module per resource
|-- components/     shared, reusable UI (badges, cards, states, dialogs)
|-- hooks/           useApiStatus, useToast
|-- pages/          one component per route
|-- types/          shared request/response types
```

## Backend integration status

The frontend is built against the **target** contract described in the
product brief (three-status reviews, RAG summaries, job requirement CRUD,
`/analyze`, filtered list, `PATCH`, file streaming). The current backend only
exposes:

```text
GET  /health
POST /v1/chat/completions
POST /api/v1/cv-reviews
GET  /api/v1/cv-reviews
GET  /api/v1/cv-reviews/{id}
```

Until the remaining routes ship, `src/api/cvReviews.ts` maps the legacy
`{ approved: boolean }` shape onto the target `CVReview` type client-side and
applies filtering/search/pagination in the browser instead of on the server.
Every response produced this way is flagged with `fromCompatibilityShim:
true`, and the review workspace shows a visible banner while it's active
&mdash; the gap is surfaced, not hidden.

Job requirement creation/editing, `/analyze`, `PATCH /cv-reviews/{id}`, and
`/cv-reviews/{id}/file` call the target routes directly and will 404 until
the backend adds them.

Once the backend has the full contract, flip:

```ts
// src/api/cvReviews.ts
export const BACKEND_HAS_FULL_CONTRACT = true;
```

and the compatibility mapping stops being used.

## Notes

- Only `VITE_`-prefixed variables belong in `frontend/.env` &mdash; anything
  prefixed that way is exposed to the browser. Never put `LLM_API_KEY`,
  `DATABASE_URL`, or MinIO credentials here.
- The RAG summary is rendered as plain text only (never `dangerouslySetInnerHTML`),
  since it's model-generated, untrusted content.
