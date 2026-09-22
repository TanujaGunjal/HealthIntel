# HealthIntel

HealthIntel is an educational health-information web application. It accepts
free-text symptoms and prescription images, extracts structured information,
retrieves supporting passages from a local medical reference collection, and
shows safety-oriented guidance. It does not diagnose conditions, prescribe
medicines, or replace a qualified clinician.

## Implemented capabilities

The following capabilities are implemented in the repository:

- JWT-authenticated registration, login, token refresh, profile management, and
  user history.
- Quick symptom analysis using a rule-based clinical entity and negation
  pipeline plus a TF-IDF/logistic-regression classifier. The classifier
  contains six categories: respiratory, digestive, neurological,
  dermatological, musculoskeletal, and general.
- A full LangGraph workflow with four logical stages:
  `SymptomAnalysisAgent`, `EvidenceRetrievalAgent`, `SafetyAgent`, and
  `FinalResponseAgent`. Routing skips retrieval/safety when no positive
  symptoms or relevant evidence is available.
- Negated symptom handling. For example, denied chest pain is excluded from
  positive symptoms and does not trigger the red-flag safety path.
- Local RAG over curated documents in `backend/data/medical_documents/`.
  Documents are chunked, embedded with `all-MiniLM-L6-v2`, indexed with FAISS,
  filtered, deduplicated, and returned with source metadata.
- Optional evidence-grounded response synthesis through the configured Gemini
  or OpenAI provider. A deterministic source-grounded fallback is used when no
  provider is configured or a provider call is unavailable.
- Prescription image analysis with EasyOCR and a Tesseract fallback. The
  pipeline cleans OCR text, extracts medicine name, dosage, frequency,
  duration, timing, confidence, and validation warnings.
- Prescription explanations grounded in the local medicine reference and RAG
  results.
- Google Calendar OAuth for authenticated users. The callback stores the
  authorized credential server-side, returns to the Prescription page, and the
  UI reports `Google Calendar Connected`. Scheduling requires a user-selected
  time, creates a recurring Google Calendar event from the extracted duration,
  and records an idempotency fingerprint to prevent duplicate local event
  records.
- Appointment create/list/detail/cancel endpoints and the corresponding UI.
- A health endpoint and a Docker Compose configuration for PostgreSQL, Redis,
  Django, Celery, and the frontend.

### Important boundaries

- Medication reminder times are not inferred. The user must select the time in
  the Prescription page before scheduling.
- OCR and NLP extraction can be incomplete or low-confidence; the UI exposes
  validation warnings rather than treating extraction as clinical truth.
- Google Calendar requires valid OAuth client configuration and a user
  authorization. Credentials and provider keys are supplied through environment
  variables and are not committed to this repository.
- Redis, external LLM providers, OCR model downloads, and the FAISS index are
  runtime dependencies that may be unavailable in a minimal local test run.
- The repository contains Docker and Celery configuration, but this README does
  not claim a production deployment or hosted-service validation.

## Architecture

```text
React + Vite frontend
        |
        v
Django REST Framework API + JWT authentication
        |
        +--> Symptom NER/negation + TF-IDF classifier
        +--> LangGraph health-information workflow
        +--> FAISS/sentence-transformers RAG
        +--> EasyOCR/Tesseract prescription pipeline
        +--> Google Calendar OAuth and event scheduling
        +--> Appointment, history, and profile persistence
        |
        +--> SQLite by default, PostgreSQL when DATABASE_URL is supplied
        +--> Redis cache/Celery broker when available
```

### Frontend

The React application is in `frontend/` and includes pages for:

- Landing, login, registration, and profile setup
- Dashboard and history
- Symptom analysis and full workflow results
- Prescription upload, extraction review, explanation, and calendar reminders
- Evidence search
- Appointments
- About/help content

The frontend uses React 19, Vite, Tailwind CSS, Axios, React Router, and
`react-hot-toast`.

### Backend and ML/RAG

The Django project is in `backend/`. The main applications are:

- `users`: authentication, profile, history, and health check
- `symptoms`: quick analysis and full workflow endpoints
- `prescriptions`: OCR analysis, medicine extraction, and explanations
- `rag`: authenticated semantic search and evidence-grounded answers
- `agents`: Celery workflow task/status support
- `appointments`: appointment CRUD and cancellation
- `calendar`: Google OAuth, connection status, disconnect, and scheduling

The ML implementation is intentionally defensive:

- `backend/ml/ner_pipeline.py` uses curated entity matching and clinical
  negation rules, with optional spaCy/scispaCy loading.
- `backend/ml/classifier.py` trains or loads a TF-IDF plus logistic-regression
  classifier over the six supported categories.
- `backend/ml/rag_engine.py` builds and queries a FAISS index over local
  reference documents.
- `backend/ml/ocr_pipeline.py` runs EasyOCR first and uses Tesseract when the
  EasyOCR result is empty or too low-confidence.
- `backend/ml/agent_workflow.py` builds the compiled LangGraph workflow and
  supports configured Gemini/OpenAI providers with a deterministic fallback.

## Local setup

### Prerequisites

- Python 3.11 or newer
- Node.js and npm
- Optional: Redis, PostgreSQL, Docker, and Tesseract
- Optional: Google Calendar OAuth client credentials
- Optional: Gemini or OpenAI API credentials

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py ingest_documents
python manage.py runserver 127.0.0.1:8000
```

On systems where a spaCy model is needed:

```powershell
python -m spacy download en_core_web_sm
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

The Vite development server normally runs at `http://localhost:5173`. The
Django development server normally runs at `http://localhost:8000`.

### Optional Celery worker

```powershell
cd backend
celery -A config worker --loglevel=info
```

### Docker Compose

```powershell
docker compose up --build
```

Compose defines PostgreSQL, Redis, Django, Celery, and an Nginx-served
frontend. Supply local environment values through an uncommitted `.env` file;
use `.env.example` as the variable-name reference.

## Environment configuration

The repository provides `.env.example`. It contains variable names only and
must not be populated with credentials in source control.

Important variables include:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django signing and application secret |
| `DATABASE_URL` | Optional database URL; SQLite is the default |
| `REDIS_URL` | Redis cache/broker URL |
| `CORS_ALLOWED_ORIGINS` | Allowed frontend origins |
| `LLM_PROVIDER` | `gemini` or the configured provider selection |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | Optional Gemini response synthesis |
| `OPENAI_API_KEY` / `OPENAI_MODEL` | Optional OpenAI response synthesis |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Google Calendar OAuth client |
| `GOOGLE_REDIRECT_URI` | Registered Google OAuth callback URL |
| `FRONTEND_URL` | Frontend URL used after OAuth callback |

## API surface

All endpoints below require JWT authentication unless marked public.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/auth/register/` | Create an account |
| `POST` | `/api/auth/login/` | Obtain access and refresh tokens |
| `POST` | `/api/auth/refresh/` | Refresh an access token |
| `GET/PATCH` | `/api/auth/profile/` | Read/update the current profile |
| `GET` | `/api/history/` | Read recent symptom and prescription history |
| `GET` | `/api/health/` | Health/status probe; public |
| `POST` | `/api/symptoms/analyze/` | Quick NER, negation, and classification |
| `POST` | `/api/symptoms/workflow/` | Run the full LangGraph workflow |
| `GET` | `/api/agents/workflow/<id>/status/` | Read an async workflow status |
| `POST` | `/api/rag/query/` | Query the local medical knowledge base |
| `POST` | `/api/prescription/analyze/` | Upload and analyze a prescription image |
| `POST` | `/api/prescription/<id>/explain/` | Generate a grounded prescription explanation |
| `GET` | `/api/calendar/status/` | Report connection and scheduled medicine IDs |
| `GET` | `/api/calendar/oauth/authorize/` | Return a Google authorization URL |
| `GET` | `/api/calendar/oauth/callback/` | Exchange the OAuth code and store credentials |
| `POST` | `/api/calendar/oauth/disconnect/` | Remove saved local calendar credentials |
| `POST` | `/api/calendar/schedule/` | Create/update a selected-time medication event |
| `GET/POST` | `/api/appointments/` | List or create appointments |
| `GET/DELETE` | `/api/appointments/<id>/` | Read or cancel an appointment |

The callback returns an HTML handoff page for browser OAuth. Direct callers
requesting JSON receive a JSON error for invalid or expired OAuth state.

## Verification

The repository includes Django/pytest tests for:

- Authentication and JWT permissions
- Health endpoint
- Symptom extraction, classification, and negation
- LangGraph compilation, routing, evidence states, and safety warnings
- RAG query validation and availability behavior
- OCR extraction and prescription validation semantics
- Prescription explanations and evidence matching
- Google Calendar authorization, callback storage, status, scheduling, and
  idempotency

Run the backend tests:

```powershell
cd backend
python manage.py test
pytest
```

Run the frontend checks:

```powershell
cd frontend
npm run lint
npm run build
```

Test results reported with this README update are based on the commands actually
run in the current checkout; no benchmark or deployment metric is asserted here
unless it is reproduced and verified.

## Repository layout

```text
backend/
  apps/              Django applications and API endpoints
  config/            Django settings, URLs, WSGI/ASGI, Celery
  data/              Curated medical reference documents
  evaluation/        Optional classifier/RAG evaluation scripts
  ml/                OCR, NER, classifier, RAG, and LangGraph code
  tests/              Pytest coverage for API and ML behavior
frontend/
  src/               React pages, components, context, and API service
docker/
  Dockerfile.backend
  Dockerfile.frontend
docker-compose.yml
.env.example
```

## Medical disclaimer

HealthIntel provides educational information only. Do not use it for emergency
decisions, diagnosis, or medication changes. Seek professional medical advice
for personal care and emergency services for urgent symptoms.
