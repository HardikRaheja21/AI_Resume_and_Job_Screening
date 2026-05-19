# AI-Powered Recruitment Intelligence Platform

An enterprise-grade FastAPI-powered resume parsing and intelligent candidate matching system with advanced features including adaptive workflows, multi-agent coordination, semantic search, and predictive runtime optimization.

## 📁 Repository Structure

```
.
├── backend/       # FastAPI backend service
├── frontend/                      # Web UI applications
│   ├── ats/                       # React + Vite ATS interface (recommended)
│   ├── index.html                 # Legacy frontend entry point
│   ├── login.html                 # Legacy login page
│   ├── dashboard.html             # Legacy dashboard
│   └── admin.html                 # Legacy admin interface
├── alembic/                       # Database migrations
├── tests/                         # End-to-end and unit tests
├── docs/                          # Documentation and architecture guides
├── scripts/                       # Utility and maintenance scripts
├── tools/                         # Development tools
├── uploads/                       # User-uploaded resume files
├── docker-compose.yml             # Docker orchestration
├── requirements.txt               # Python dependencies
├── package.json                   # Node.js dependencies (root)
└── README.md                      # This file
```

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+ (for frontend)
- PostgreSQL 14+ (production) or SQLite (development)
- Redis 6+ (optional, for async processing)

### Backend Setup

```bash
# Clone and navigate to project root

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your actual values
```

### Database Initialization

```bash
# Apply migrations
alembic upgrade head

# To create a new migration after schema changes:
alembic revision -m "describe_your_change" --autogenerate
```

### Backend Startup

```bash
# From repository root
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://127.0.0.1:8000`
Swagger docs: `http://127.0.0.1:8000/docs`

### Frontend Setup

The frontend is built with **React + Vite**. Choose one:

#### Option A: Run the Modern React Frontend (Recommended)

```bash
cd frontend/ats

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# VITE_API_BASE_URL should point to your backend

# Development server
npm run dev

# Production build
npm run build
```

Access at `http://localhost:5173`

#### Option B: Legacy Frontend (Served by Backend)

Accessible directly from backend:
- Dashboard: `http://127.0.0.1:8000/frontend/dashboard.html`
- Login: `http://127.0.0.1:8000/frontend/login.html`
- Admin: `http://127.0.0.1:8000/frontend/admin.html`

## 🐳 Docker Deployment

### Run with Docker Compose

```bash
# Start all services (backend, PostgreSQL, Redis)
docker-compose up -d

# View logs
docker-compose logs -f backend

# Stop services
docker-compose down
```

### Build Custom Image

```bash
docker build -t resume-parser:latest .
docker run -p 8000:8000 \
  -e DATABASE_URL="postgresql+psycopg2://user:pass@host:5432/resume_db" \
  -e JWT_SECRET_KEY="replace_with_secure_random_secret" \
  -e CORS_ORIGINS="https://your-frontend.vercel.app" \
  -e OPENAI_API_KEY="sk-..." \
  resume-parser:latest
```

## 📚 API Documentation

All API endpoints are protected with JWT authentication (except `/auth` endpoints).

### Core Endpoints

**Authentication**
- `POST /auth/signup` - Create account
- `POST /auth/login` - Login (returns JWT token)
- `POST /auth/register` - Legacy signup alias

**Resume Management**
- `POST /resumes/upload` - Upload resume and match with JD
- `GET /resumes` - List user's resumes
- `GET /resumes/{resume_id}` - Get resume details
- `PATCH /resumes/{resume_id}` - Update resume metadata
- `DELETE /resumes/{resume_id}` - Delete resume
- `GET /resumes/search` - Search resumes by email/name/score/date

**Analytics & Reporting**
- `GET /resumes/stats` - Summary analytics (total/selected/rejected/avg score)
- `GET /features/analytics/funnel` - Funnel analytics by stage
- `GET /features/analytics/time-to-shortlist` - Shortlist speed metrics
- `GET /features/export/csv` - Export candidates as CSV

**AI Features**
- `GET /features/resumes/{resume_id}/ai-summary` - AI-generated candidate summary
- `GET /features/resumes/{resume_id}/interview-questions` - Generate interview questions
- `POST /features/resumes/{resume_id}/interview/start` - Start adaptive interview
- `POST /features/interviews/{session_id}/answer` - Submit interview answer

**Integrations**
- `POST /features/notify/slack` - Send Slack message
- `POST /features/notify/teams` - Send Teams message
- `POST /features/integrations/ats-sync/{resume_id}` - Sync to ATS webhook
- `GET /features/integrations/status` - Check integration status

**Admin**
- `GET /features/team/summary` - Team analytics (admin only)
- `GET /features/admin/users` - List users (admin only)
- `PATCH /features/admin/users/{user_id}/role` - Update user role (admin only)

**Health**
- `GET /healthz` - Service liveness probe
- `GET /readyz` - Readiness probe (checks DB and upload dir)

### Upload Endpoint Field Variations

The upload endpoint accepts flexible field names for compatibility:
- Resume files: `files`, `resumes`, or `file`
- Job description text: `jd_text`, `job_description`, or `jd`
- Job description file: `jd_file`

**Example:**
```bash
curl -X POST http://localhost:8000/resumes/upload \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "file=@resume.pdf" \
  -F "jd_text=<job description>"
```

## ⚙️ Configuration

### Backend Environment Variables

Key variables (full list in `backend/.env.example`):

```env
# Database
DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/resume_db

# Authentication
JWT_SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=https://your-frontend.vercel.app

# LLM / AI
OPENAI_API_KEY=sk-your-key
OPENAI_MODEL=gpt-4o-mini

# Async Processing
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0

# Integrations
SLACK_WEBHOOK_URL=https://hooks.slack.com/...
TEAMS_WEBHOOK_URL=https://outlook.webhook.office.com/...
ATS_SYNC_URL=https://your-ats.com/webhook
```

### Frontend Environment Variables

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
VITE_APP_NAME=AI Recruiter ATS
```

## 🧪 Testing

### End-to-End Tests (Playwright)

```bash
# From project root
npm install -D @playwright/test

# Run tests
npx playwright test

# Run in UI mode
npx playwright test --ui
```

### Backend Unit Tests

```bash
# Run tests
pytest backend/tests

# Run with coverage
pytest backend/tests --cov=backend --cov-report=html
```

## 📖 Documentation

See the [docs/](docs/) folder for:
- [Async Processing Architecture](docs/async-processing-architecture.md) - Design of async job processing
- [ATS Productization Plan](docs/ats-productization-plan.md) - Roadmap and feature planning

## 🔧 Development

### Backend Code Organization

```
backend/
├── main.py                    # FastAPI app initialization
├── database.py                # SQLAlchemy setup
├── models.py                  # ORM models
├── auth/                      # Authentication (JWT, user management)
├── integrations/              # External service integrations
├── resume_parser_service/     # Core resume parsing logic
├── routers/                   # API route handlers
├── services/                  # Business logic layer
├── workers/                   # Async task workers (Celery)
├── utils/                     # Utility functions
└── tests/                     # Unit and integration tests
```

### Common Development Commands

```bash
# Backend
python -m uvicorn backend.main:app --reload

# Frontend (modern)
cd frontend/ats
npm run dev

# Database migration
alembic revision -m "add_column" --autogenerate
alembic upgrade head

# Run linter
flake8 backend
black backend

# Format frontend
cd frontend/ats && npm run format
```

## Deployment

### Frontend on Vercel

Deploy the Vite app from `frontend/ats`.

Vercel settings:
- Root Directory: `frontend/ats`
- Framework Preset: `Vite`
- Build Command: `npm run build`
- Output Directory: `dist`

Required Vercel environment variable:
- `VITE_API_BASE_URL=https://your-backend-url`

`frontend/ats/vercel.json` defines the Vite build output and SPA rewrite.

### Backend on Render

Use `render.yaml`, or create a Web Service manually.

Render settings:
- Runtime: Python
- Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
- Start Command: `alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/healthz`

Required Render environment variables:
- `DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database`
- `JWT_SECRET_KEY=<secure random value>`
- `CORS_ORIGINS=https://your-frontend.vercel.app`

Recommended Render environment variables:
- `AUTO_DB_BOOTSTRAP=false`
- `UPLOAD_DIR=/tmp/uploads`
- `LOG_FILE=/tmp/resume-parser-api.log`
- `DEAD_LETTER_DIR=/tmp/dead_letters`
- `VECTOR_DB_DIR=/tmp/vector_store`
- `MATCHER_DISABLE_EMBEDDINGS=true` for smaller starter instances
- `OPENAI_API_KEY=<optional>`
- `REDIS_URL=<managed redis url>` if async/event streaming is enabled
- `CELERY_BROKER_URL=<managed redis url>` if running workers
- `CELERY_RESULT_BACKEND=<managed redis url>` if running workers

### Backend on Railway

Use `railway.json`.

Railway setup:
- Add a PostgreSQL service.
- Set `DATABASE_URL` from the Railway PostgreSQL connection string.
- Set `JWT_SECRET_KEY`.
- Set `CORS_ORIGINS` to the deployed Vercel frontend URL.
- Deploy from the repository root.

Railway start command:

```bash
alembic upgrade head && uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

### Docker Production

Build and run:

```bash
docker build -t resume-parser-api .
docker run --rm -p 8000:8000 \
  -e PORT=8000 \
  -e DATABASE_URL="postgresql+psycopg2://user:password@host:5432/resume_db" \
  -e JWT_SECRET_KEY="replace_with_secure_random_secret" \
  -e CORS_ORIGINS="https://your-frontend.vercel.app" \
  resume-parser-api
```

Local full stack:

```bash
docker-compose up -d --build
```

Docker Compose runs PostgreSQL, Redis, API, and workers, applies Alembic migrations before API start, and persists uploads, logs, dead letters, vector store data, Postgres, and Redis in Docker volumes.

### Production Checks

Before deployment:
- `cd frontend && npm run build`
- `cd frontend && npm run lint`
- `python -c "import backend.main as m; print(m.app.title)"`
- `uvicorn backend.main:app --host 0.0.0.0 --port 8000`

Production requirements:
- Use PostgreSQL, not SQLite.
- Set a strong `JWT_SECRET_KEY`.
- Set `CORS_ORIGINS` to the exact Vercel domain, comma-separated if there is more than one origin.
- Keep `AUTO_DB_BOOTSTRAP=false`; use Alembic migrations.
- Use persistent storage or object storage for uploads if uploaded resumes must survive platform restarts.
- Use managed Redis when async processing, workers, or realtime processing events are enabled.

## 🤝 Contributing

### Code Style

- **Python**: Follow PEP 8 (checked with Black, Flake8)
- **TypeScript/React**: Use ESLint and Prettier
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

### Pull Request Process

1. Create a branch: `git checkout -b feature/your-feature`
2. Make changes and test thoroughly
3. Commit with clear messages
4. Push and create a pull request
5. Ensure CI/CD passes
6. Request review from maintainers

## 📝 License

[Add your license here]

## 📧 Support

For issues, questions, or feature requests:
- GitHub Issues: [Link to issues]
- Email: support@example.com
- Documentation: See [docs/](docs/) folder

---

**Last Updated**: 2026-05-19
**Version**: 1.0.0

Password policy for signup/register:
- At least 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number

Security and hardening:
- Login rate limiting for repeated failed attempts (`LOGIN_RATE_LIMIT_ATTEMPTS`, `LOGIN_RATE_LIMIT_WINDOW_SECONDS`)
- Upload type and MIME validation
- Upload size limit (`MAX_UPLOAD_FILE_SIZE_MB`)
- Duplicate-safe file storage names
- Duplicate candidate linking (`duplicate_of_id`) by owner+email during upload
- Webhook and SMTP retry strategy with exponential backoff + dead-letter capture (`DEAD_LETTER_DIR`)

AI behavior:
- `/features/resumes/{resume_id}/ai-summary` and `/features/resumes/{resume_id}/interview-questions` use OpenAI when `OPENAI_API_KEY` is configured.
- If AI is not configured or provider fails, endpoints automatically fall back to deterministic heuristic output.
- Semantic search uses sentence-transformer embeddings with optional ChromaDB vector retrieval when available and falls back to token overlap on failure.
- The new `/features/semantic-retrieve` endpoint returns ranked recruiter candidates with chunk-level resume hits for skills, projects, experience, and education.
- Adaptive interview scoring currently uses deterministic keyword/concept heuristics with difficulty adjustment, and stores interview/final scores on each resume.

## Tests

```bash
pytest backend/tests -q
```

Smoke check:

```bash
python scripts/smoke_check.py
```

HTTP smoke check (when server is running):

```bash
SMOKE_BASE_URL=http://127.0.0.1:8000 python scripts/smoke_check.py
```

## Error Format

API errors return a standard envelope and keep backward-compatible `detail`:
- `error.code` (for example: `validation_error`, `unauthorized`, `not_found`)
- `error.message`
- `error.request_id` (also returned as `X-Request-ID` response header)
- `detail` (legacy-compatible field)

## Key Environment Variables

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `AUTO_DB_BOOTSTRAP`
- `UPLOAD_DIR`
- `MAX_UPLOAD_FILE_SIZE_MB`
- `LOGIN_RATE_LIMIT_ATTEMPTS`
- `LOGIN_RATE_LIMIT_WINDOW_SECONDS`
- `LOG_FILE`
- `WEBHOOK_TIMEOUT_SECONDS`
- `WEBHOOK_RETRY_ATTEMPTS`
- `WEBHOOK_RETRY_BACKOFF_SECONDS`
- `EMAIL_RETRY_ATTEMPTS`
- `EMAIL_RETRY_BACKOFF_SECONDS`
- `DEAD_LETTER_DIR`
- `SLACK_WEBHOOK_URL`
- `TEAMS_WEBHOOK_URL`
- `ATS_SYNC_URL`
- `ATS_SYNC_API_KEY`
- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `OPENAI_TIMEOUT_SECONDS`
- `MATCHER_DISABLE_EMBEDDINGS`

Docker compose production behavior:
- Runs `alembic upgrade head` before starting API
- Persists uploads and app logs via docker volumes

Database migration note:
- Alembic is the migration source of truth.
- Startup bootstrap table creation is disabled by default (`AUTO_DB_BOOTSTRAP=false`) and intended only for local/dev convenience.
