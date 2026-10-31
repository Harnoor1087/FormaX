# FormaX AI

## Run locally

Install frontend dependencies and start the React app:

```powershell
npm install
npm run dev
```

The frontend is at `http://localhost:3001`. Without the root `.env` configuration it runs
in mock mode.

Start the FastAPI backend in a second terminal:

```powershell
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8002
```

Set `VITE_API_URL=http://localhost:8002` and `VITE_USE_MOCK=false` in the root `.env`
to use the backend instead of mock data. Start the backend using the project virtual
environment if one is configured, for example `.venv\\Scripts\\python.exe` on Windows.

For non-mock mode, configure separate server-side API tokens in the same root `.env`.
Generate strong values (32 random bytes each) with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Assign one generated value to `OPERATOR_API_TOKEN` and a different generated value
to `REVIEWER_API_TOKEN`. Restart the backend after changing `.env`. In the UI, paste
the appropriate token and select **Connect**. The token remains in browser memory only.
Operator tokens can generate and view records. Reviewer tokens can also edit, approve,
and export. If tokens are not configured, protected endpoints return HTTP 503; missing
or invalid tokens return HTTP 401.

For Gemini-backed drafts, add `GEMINI_API_KEY` to the root `.env` and install backend
dependencies with `python -m pip install -r backend/requirements.txt`. The default text
model is `gemini-3.8-flash`; override it with `MODEL_NAME` if needed. Without a key, the
app explicitly labels output as template-based. If Gemini is temporarily unavailable
(HTTP 503) or request quota is exhausted (HTTP 429), FormaX labels the affected output
as a template fallback. Other provider errors are reported rather than silently switching
to templates.

## Member 1 → backend contract

`POST /api/generate` accepts `source_text`, `source_type`, `source_filename`,
`output_types`, `audience`, `tone`, `language`, `detail_level`, and `objective`.
The response contains generated outputs plus a request/generation ID and validation
results. Errors use a non-2xx status with a `detail` field.

## Member 3: generation review and persistence

Generated output uses a shared typed response schema with per-format structure checks.
The deterministic consistency check verifies that every draft retains the shared topic
and that listed key points match the analyzed facts; approval is blocked if either
validation check fails.

Generation records, sanitized source/context, generated drafts, review status, and
edit/approval/export events are stored in SQLite. The default database is
`backend/data/formax.sqlite3`; set `FORMAX_DATABASE_PATH` to override it.

- `GET /api/v1/generations` — list saved generations
- `GET /api/v1/generations/{generation_id}` — get outputs and review audit events
- `PATCH /api/v1/outputs/{output_id}` — save an edited draft (resets approval)
- `POST /api/v1/outputs/{output_id}/approve` — approve a validated draft
- `POST /api/v1/outputs/{output_id}/export` — record export of an approved draft
- `POST /api/v1/outputs/{output_id}/presentation.pptx` — download an approved presentation as a PowerPoint deck
- `POST /api/v1/outputs/{output_id}/video` — start an optional Veo MP4 render for an approved video package
- `GET /api/v1/video-jobs/{video_job_id}` — check render progress
- `GET /api/v1/video-jobs/{video_job_id}/download` — download the approved MP4

The History view loads saved generations when the frontend is connected to the backend.
TXT, Markdown, and JSON downloads are enabled only after approval; the backend records
each approved export action. Approved presentation drafts also have a **PPTX** button
that creates and downloads an editable PowerPoint deck with one slide per slide section.

### Render an MP4 with Google Veo

Set `GEMINI_API_KEY` in the root `.env` to a Google AI API key with Veo access and restart
the backend. Generate a **Video package**, review it, and approve it; the reviewer UI will
then offer **Render 8-second MP4**. Rendering is an explicit action (and may incur provider
charges): it creates one 8-second, 720p, 16:9 clip with generated audio. FormaX polls Veo,
saves the MP4 under `backend/data/videos/` by default, and presents a preview and download
button. Set `FORMAX_VIDEO_DIR` to change that storage directory. Render jobs and review
events persist in SQLite. Editing the approved brief invalidates its prior render and
requires approval before a replacement can be requested. Selecting **Video package**
creates the written script/storyboard only; an MP4 is produced only after the separate
render action succeeds. Actual rendering depends on Google Veo access, quota, and billing.

See Google's [Veo Gemini API guide](https://ai.google.dev/gemini-api/docs/veo) for current
model access, availability, and provider billing details.

## Prototype scope and remaining work

The Member 3 MVP path is implemented: all seven format handlers, output-shape checks,
source-topic and key-point checks, SQLite history, review actions, and TXT/Markdown/JSON
export. With `GEMINI_API_KEY`, the generators use Gemini to draft each selected format.
Without a key, the app uses clearly labeled deterministic templates. Automated consistency checks compare the shared topic and listed key points with analyzed
context; they do not semantically fact-check every sentence in an output body. Human
review is still required before approval.

Authentication is implemented using distinct server-side operator/reviewer bearer tokens.
Before production deployment, add a user/token provisioning and rotation workflow,
use HTTPS, and strengthen whole-body semantic fact checking. Video rendering currently
produces one short 8-second Veo clip per approved brief; longer multi-scene assembly,
caption burn-in, and production-scale media retention remain future work.

Run backend tests with `cd backend; python -m pytest -q`.
