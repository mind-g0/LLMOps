# Frontend Team Instructions

Build a new frontend from scratch using:

- React.js
- Vite
- TypeScript
- Tailwind CSS
- React Router

The current frontend folder is empty. Put the new project in:

```text
app/frontend/
```

## Product Goal

The frontend is an HR CV review application. A user will:

1. Read about the team and product.
2. Define three job requirements.
3. Upload up to 10 CVs.
4. Start the CV processing workflow.
5. Review processed CVs and their RAG results.
6. Approve or reject CVs that require human review.
7. View all CVs and their current statuses.

## Frontend Environment

Create `app/frontend/.env.example`:

```env
VITE_API_BASE_URL=http://localhost:8004
```

Each developer creates a local `app/frontend/.env` with the same variable.

Use it like this:

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
```

Do not put these secrets in the frontend environment:

```text
LLM_API_KEY
DATABASE_URL
MINIO_ACCESS_KEY
MINIO_SECRET_KEY
```

Anything prefixed with `VITE_` is exposed in the browser.

## Required Routes

Use these frontend routes:

```text
/                   Page 1: team and product introduction
/setup              Page 2: job requirements and CV upload
/review             Page 3: processed CV review workspace
/cvs                Page 4: all CVs
```

Add a shared layout with:

- Product logo/name
- Navigation links for all four pages
- Current API connection status
- Responsive mobile navigation
- Consistent status colors

## Page 1: Team and Product

Route:

```text
/
```

Purpose: introduce who we are and what the product does.

Content:

- Team name and short description
- Product purpose: use RAG and LLM evaluation to help review CVs
- Short explanation of the workflow
- Team roles or members
- Button: `Start a review` -> `/setup`
- Button: `View all CVs` -> `/cvs`

This page is informational. It does not call the RAG pipeline.

## Page 2: Job Requirements and Upload

Route:

```text
/setup
```

This page has two sections.

### Section A: Job Requirements

Show three editable requirement panels:

```text
Job 1
Job 2
Job 3
```

Each job requirement should support:

- Job name
- Job title
- Description
- Required skills
- Required experience
- Education or certification requirements
- Save and edit actions

Use one reusable component and render it three times. Do not create three
separate hard-coded implementations.

Suggested object:

```ts
interface JobRequirement {
  id?: string;
  name: string;
  title: string;
  description: string;
  requirements: string[];
}
```

### Section B: CV Upload

Requirements:

- Allow multiple file selection.
- Maximum 10 CV files per process.
- Show selected files before upload.
- Allow removing a selected file.
- Show filename and file size.
- Validate file type and size in the browser.
- Show upload progress or processing state.
- Disable `Start process` when there are no files or no job requirement.

Accepted file types will be confirmed by the backend, but initially support:

```text
.pdf
.docx
```

Buttons:

```text
Add CVs
Start process
Clear
```

When `Start process` is clicked, send the selected files and the selected job
requirement to the backend analysis endpoint. The process may be asynchronous,
so the page must support a processing state and an error state.

Planned request:

```http
POST /api/v1/cv-reviews/analyze
Content-Type: multipart/form-data
```

Fields:

```text
cv: one or more uploaded files
job_requirement_id: selected job requirement UUID
```

After starting the process, navigate to `/review` or show a button to open the
review workspace.

## Page 3: Processed CV Review Workspace

Route:

```text
/review
```

Use a three-area desktop layout.

### Left Sidebar: CV List by Status

The left sidebar contains the processed CVs grouped or filtered by status:

- Approved: green
- Needs human review: amber/orange
- Not approved: red

Each CV item should show:

- CV filename
- Current status badge
- Job requirement name
- Processing date

Clicking a CV selects it and loads its review details in the main area.

### Center: Selected CV Result

Show the selected CV's:

- Filename
- Status
- Job requirement
- Short RAG summary
- Extracted candidate strengths
- Missing requirements
- Matching requirements
- Rejection reason, if available
- Processing timestamp
- Link to view/download the original CV

The RAG summary should be treated as untrusted text and rendered safely. Do not
render raw HTML from the model response.

Suggested future response shape:

```ts
interface CVReview {
  id: string;
  cv_name: string;
  status: "approved" | "not_approved" | "needs_human_review";
  rag_summary: string | null;
  strengths: string[];
  missing_requirements: string[];
  rejection_reason: string | null;
  job_requirement_id: string;
  job_requirement_name: string;
  cv_file_url?: string;
  created_at: string;
}
```

### Bottom-Right: Human Review Actions

Only show these buttons when the selected CV has status
`needs_human_review`:

```text
Approve
Not approved
```

When the user clicks `Approve`:

```http
PATCH /api/v1/cv-reviews/{id}
```

```json
{
  "status": "approved",
  "rejection_reason": null
}
```

When the user clicks `Not approved`:

```http
PATCH /api/v1/cv-reviews/{id}
```

```json
{
  "status": "not_approved",
  "rejection_reason": "Reason entered by the reviewer"
}
```

The rejection reason may be empty until the backend/product team finalizes the
policy. If the UI collects a reason, provide a small confirmation dialog.

After a successful update:

1. Update the selected CV status.
2. Move it to the correct sidebar group.
3. Refresh the dashboard counts.
4. Show a success notification.

## Page 4: All CVs

Route:

```text
/cvs
```

Show every CV in a table on desktop and cards on mobile.

Columns or card fields:

- CV name
- Status
- Job requirement
- RAG summary preview
- Rejection reason preview
- Created date
- View details action
- View/download CV action

Controls:

- Search by filename
- Filter by status
- Filter by job requirement
- Sort newest/oldest
- Pagination
- Empty state
- Loading state
- Error state with retry

Status filter values:

```text
all
approved
needs_human_review
not_approved
```

## Current Backend Routes

These routes currently exist:

| Method | Route                     | Purpose                     |
| ------ | ------------------------- | --------------------------- |
| `GET`  | `/health`                 | Check API availability      |
| `POST` | `/v1/chat/completions`    | LLM/OCR gateway             |
| `POST` | `/api/v1/cv-reviews`      | Upload CV and save a review |
| `GET`  | `/api/v1/cv-reviews`      | List CV reviews             |
| `GET`  | `/api/v1/cv-reviews/{id}` | Get one CV review           |

Current review response:

```json
{
  "id": "uuid",
  "cv_name": "candidate.pdf",
  "approved": false,
  "rejection_reason": null,
  "cv_object_key": "cvs/uuid/candidate.pdf",
  "created_at": "2026-09-21T10:00:00Z"
}
```

The current backend does not yet have the three-status field, RAG summary,
job requirement routes, file-view route, update route, or analyze route.
Those are listed in `UNCOMPLETED_BACKEND.md`.

For the first integration, the frontend may use the current list/get routes and
show a temporary compatibility mapping, but it must not hide the missing backend
functionality.

## Backend Routes Required Before Full Integration

The frontend needs these routes from the backend team:

```http
GET    /api/v1/job-requirements
POST   /api/v1/job-requirements
GET    /api/v1/job-requirements/{id}
PATCH  /api/v1/job-requirements/{id}
DELETE /api/v1/job-requirements/{id}

POST   /api/v1/cv-reviews/analyze
GET    /api/v1/cv-reviews?status=&job_requirement_id=&search=&page=&page_size=
PATCH  /api/v1/cv-reviews/{id}
GET    /api/v1/cv-reviews/{id}/file
```

The final backend review object must support:

```text
approved
not_approved
needs_human_review
```

The backend must never expose MinIO credentials. It should return a secure
short-lived file URL or stream the CV file through the API.

## API Client Rules

Create one API client module. Do not call `fetch` directly from every page.

The client must:

- Prefix all routes with `VITE_API_BASE_URL`.
- Parse JSON errors consistently.
- Handle `401`, `404`, `422`, `500`, `502`, and `503`.
- Support `FormData` uploads without manually setting `Content-Type`.
- Expose typed request and response functions.
- Cancel requests when a page unmounts where appropriate.

## UI Rules

- Use Tailwind CSS for styling.
- Use reusable components for badges, tables, cards, dialogs, and buttons.
- Keep status colors consistent everywhere.
- Do not use API keys or database credentials in browser code.
- Do not show raw backend stack traces to users.
- Support desktop and mobile layouts.
- Include loading, empty, error, and retry states for every data view.
- Confirm destructive actions.
- Make keyboard focus and form labels accessible.

## Suggested Project Structure

```text
app/frontend/
|-- src/
|   |-- api/
|   |   |-- client.ts
|   |   |-- cvReviews.ts
|   |   `-- jobRequirements.ts
|   |-- components/
|   |   |-- AppLayout.tsx
|   |   |-- StatusBadge.tsx
|   |   |-- CvSidebar.tsx
|   |   |-- CvDetail.tsx
|   |   |-- HumanReviewActions.tsx
|   |   |-- JobRequirementCard.tsx
|   |   |-- CvUpload.tsx
|   |   `-- LoadingState.tsx
|   |-- pages/
|   |   |-- HomePage.tsx
|   |   |-- SetupPage.tsx
|   |   |-- ReviewWorkspacePage.tsx
|   |   `-- AllCvsPage.tsx
|   |-- types/
|   |   |-- cvReview.ts
|   |   `-- jobRequirement.ts
|   |-- App.tsx
|   `-- main.tsx
|-- .env.example
|-- package.json
|-- tailwind.config.ts
`-- vite.config.ts
```

## Completion Checklist

- [ ] React/Vite/TypeScript/Tailwind project created in `app/frontend/`.
- [ ] `.env.example` contains only `VITE_API_BASE_URL`.
- [ ] Four routes are implemented.
- [ ] Page 1 explains the team and product.
- [ ] Page 2 edits Job 1, Job 2, and Job 3.
- [ ] Page 2 limits uploads to 10 CVs.
- [ ] Page 2 has a working `Start process` state.
- [ ] Page 3 has the left CV status sidebar.
- [ ] Page 3 shows the selected CV's RAG summary.
- [ ] Page 3 shows Approve/Not approved for human review items.
- [ ] Page 4 lists all CVs with search and filters.
- [ ] API calls are centralized and typed.
- [ ] No secrets are exposed in frontend code.
- [ ] Backend gaps are tracked and coordinated before final integration.
