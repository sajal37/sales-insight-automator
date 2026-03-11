# 🐇 Sales Insight Automator — Rabbitt AI

> **Upload sales data. Get an AI-generated executive brief. Delivered to your inbox in seconds.**

[![CI Pipeline](https://github.com/sajal37/sales-insight-automator/actions/workflows/ci.yml/badge.svg)](https://github.com/sajal37/sales-insight-automator/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

🌐 **Live Frontend:** https://sales-insight-automator-red.vercel.app  
📡 **Live API / Swagger:** https://sales-insight-automator-ds0d.onrender.com/docs

---

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Features](#features)
- [Quick Start (Docker Compose)](#quick-start-docker-compose)
- [Manual Setup](#manual-setup)
- [Security Overview](#security-overview)
- [API Documentation](#api-documentation)
- [CI/CD Pipeline](#cicd-pipeline)
- [Deployment](#deployment)
- [Environment Variables](#environment-variables)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)

---

## Overview

The **Sales Insight Automator** is a full-stack application that allows team members to:

1. **Upload** a `.csv` or `.xlsx` sales data file
2. **Analyze** the data using Pandas to extract key KPIs
3. **Generate** charts (revenue by region, category, and monthly trend)
4. **Generate** a structured JSON summary using an LLM (Gemini / Groq) with fallback + retry
5. **Deliver** the summary with inline charts as a branded HTML email via Resend (SMTP fallback)

Built as a containerized, production-ready prototype for the Rabbitt AI sales team.

### v2.0 Highlights

- **Async job queue** — uploads return instantly with a job ID; a Redis-backed worker processes in the background
- **SQLite job persistence** — full lifecycle tracking (pending → processing → completed/failed)
- **LLM structured output** — validated JSON with `executive_summary`, `key_trends`, `regional_analysis`, `product_insights`, `anomalies`, `recommendations`
- **Primary + fallback LLM** — Gemini primary, Groq fallback (configurable), 2× retry with exponential backoff
- **Chart generation** — 3 high-res PNGs via matplotlib (revenue by region, category, trend)
- **Email with inline charts** — base64-embedded images in branded HTML; SMTP fallback if Resend fails
- **Structured JSON logging** — every log line is JSON with `timestamp`, `level`, `logger`, optional `job_id`
- **Graceful degradation** — if Redis is unavailable, falls back to sync processing automatically

---

## Architecture

```
┌─────────────────────────┐         ┌──────────────────────────────────────────────┐
│   Frontend (Next.js)    │  HTTPS  │         Backend (FastAPI v2)                  │
│   ─────────────────     │ ──────► │    ────────────────────────────               │
│   • Drag & drop upload  │         │   POST /upload → validate → enqueue          │
│   • Real-time SSE       │         │   GET  /jobs/{id} → poll status              │
│   • Summary preview     │         │                                              │
│   • Dark mode           │         │   ┌──────────────────────────────────────┐   │
│                         │         │   │  Redis Queue (sia:jobs)              │   │
│   Vercel / Docker       │         │   └──────────────┬───────────────────────┘   │
│                         │         │                  │                            │
│                         │         │   ┌──────────────▼───────────────────────┐   │
│                         │         │   │  Worker Process                      │   │
│                         │         │   │  ┌────────┐ ┌──────────┐ ┌────────┐ │   │
│                         │         │   │  │ Parser │→│ Analyzer │→│ Charts │ │   │
│                         │         │   │  └────────┘ └────┬─────┘ └───┬────┘ │   │
│                         │         │   │                  │           │       │   │
│                         │         │   │           ┌──────▼───────┐  │       │   │
│                         │         │   │           │ LLM Engine   │  │       │   │
│                         │         │   │           │ Gemini→Groq  │  │       │   │
│                         │         │   │           │ retry+fallbk │  │       │   │
│                         │         │   │           └──────┬───────┘  │       │   │
│                         │         │   │                  │          │       │   │
│                         │         │   │           ┌──────▼──────────▼─────┐ │   │
│                         │         │   │           │ Mailer (Resend→SMTP) │ │   │
│                         │         │   │           │ HTML + inline charts │ │   │
│                         │         │   │           └──────────────────────┘ │   │
│                         │         │   └──────────────────────────────────────┘   │
│                         │         │                                              │
│                         │         │   ┌───────────────┐  ┌───────────────┐       │
│                         │         │   │ SQLite (jobs)  │  │ Charts (PNG) │       │
│                         │         │   └───────────────┘  └───────────────┘       │
└─────────────────────────┘         └──────────────────────────────────────────────┘
```

---

## Features

### Core Flow

- ✅ CSV & XLSX file upload with client-side validation
- ✅ Magic-byte file type detection (not just extension checking)
- ✅ Enhanced analytics via Pandas (revenue by region/category, trends, outliers, MoM growth)
- ✅ 3 auto-generated charts (matplotlib): revenue by region, by category, monthly trend
- ✅ Structured JSON AI brief (Gemini 2.0 Flash / Groq Llama 3.3 70B) with validated schema
- ✅ Primary + fallback LLM with 2× retry and exponential backoff
- ✅ Branded HTML email with inline charts via Resend (SMTP fallback)
- ✅ Async job queue (Redis) — upload returns instantly, worker processes in background
- ✅ Job status polling endpoint with full lifecycle tracking
- ✅ SQLite job persistence database
- ✅ Swagger + ReDoc API documentation

### Frontend Extras

- ✅ Real-time progress via Server-Sent Events (SSE)
- ✅ Client-side file preview (first 5 rows rendered instantly)
- ✅ Summary preview with markdown rendering before sending
- ✅ Editable email subject line
- ✅ Dark mode with system preference detection
- ✅ Upload history sidebar (localStorage)
- ✅ Confetti animation on success 🎉
- ✅ Responsive design (mobile-friendly)

### Security

- ✅ API key authentication (`X-API-Key` header)
- ✅ Rate limiting (10 req/min per IP)
- ✅ CORS origin whitelist
- ✅ CSV injection sanitization
- ✅ File size & row count guards
- ✅ Security headers (HSTS, X-Frame-Options, etc.)
- ✅ Non-root Docker containers
- ✅ No stack traces leaked to clients
- ✅ Timing-safe key comparison (`secrets.compare_digest`)

### DevOps

- ✅ Multi-stage Docker builds (~150MB backend, ~80MB frontend)
- ✅ Docker Compose with Redis, API, Worker, and Frontend services
- ✅ GitHub Actions CI (lint, test, build, security audit)
- ✅ Docker healthchecks
- ✅ Structured JSON logging (every line is machine-parseable)
- ✅ Smoke test script (`scripts/smoke_test.py`)
- ✅ `.env.example` files for all services

---

## Quick Start (Docker Compose)

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose installed

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/sajal37/sales-insight-automator.git
cd sales-insight-automator

# 2. Create environment files from templates
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env.local

# 3. Edit backend/.env with your real API keys:
#    - API_KEY              → A strong random secret for auth
#    - GEMINI_API_KEY       → From Google AI Studio
#    - GROQ_API_KEY         → From groq.com (for fallback LLM)
#    - RESEND_API_KEY       → From resend.com
#    - ALLOWED_ORIGINS      → http://localhost:3000
#    (Redis, SQLite, charts are auto-configured in Docker Compose)

# 4. Edit frontend/.env.local:
#    - NEXT_PUBLIC_API_KEY → Same value as API_KEY above

# 5. Launch everything (API + Worker + Redis + Frontend)
docker compose up --build

# 6. Access the app
# Frontend:  http://localhost:3000
# Backend:   http://localhost:8000
# Swagger:   http://localhost:8000/docs
# ReDoc:     http://localhost:8000/redoc
```

---

## Manual Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Run the API server
uvicorn app.main:app --reload --port 8000

# (Optional) Run the background worker (requires Redis running)
python -m app.worker

# Run tests
pytest tests/ -v

# Run smoke test against running server
python ../scripts/smoke_test.py http://localhost:8000 YOUR_API_KEY
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Set up environment
cp .env.example .env.local
# Edit .env.local with your API URL and key

# Run the dev server
npm run dev

# Open http://localhost:3000
```

---

## Security Overview

### How Endpoints Are Secured

| Layer                  | Implementation                                                                                              | Purpose                                                                 |
| ---------------------- | ----------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| **Authentication**     | `X-API-Key` header validated via `secrets.compare_digest`                                                   | Prevents timing attacks; ensures only authorized clients access the API |
| **Rate Limiting**      | `slowapi` at 10 req/min per IP                                                                              | Prevents abuse and resource exhaustion                                  |
| **CORS**               | Explicit origin whitelist in `ALLOWED_ORIGINS`                                                              | Blocks unauthorized cross-origin requests                               |
| **File Validation**    | Magic byte detection + extension check + size cap (50MB) + row cap (100K)                                   | Prevents upload of malicious files                                      |
| **CSV Injection**      | Strips `=`, `+`, `-`, `@`, `\t`, `\r` prefixes from cell values                                             | Prevents formula injection when data is re-exported                     |
| **Security Headers**   | `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS`, `Referrer-Policy`, `Permissions-Policy` | Defense-in-depth against XSS, clickjacking, MIME sniffing               |
| **Error Handling**     | Generic error messages to clients; full logs server-side                                                    | No information leakage                                                  |
| **Container Security** | Non-root `appuser` in both Docker images                                                                    | Principle of least privilege                                            |
| **Input Validation**   | Pydantic `EmailStr` for email, `UploadFile` type constraints                                                | Prevents injection via malformed inputs                                 |
| **Dependency Audit**   | `pip-audit` + `npm audit` in CI pipeline                                                                    | Catches known CVEs in dependencies                                      |

---

## API Documentation

Once the backend is running, access:

- **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
- **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

### Key Endpoints

| Method | Path                       | Description                                           |
| ------ | -------------------------- | ----------------------------------------------------- |
| `GET`  | `/api/v1/health`           | Health check (public) — includes Redis + DB status    |
| `POST` | `/api/v1/upload`           | Upload & enqueue — returns job ID + status URL        |
| `GET`  | `/api/v1/jobs/{job_id}`    | Poll job status (analytics, LLM result, email status) |
| `POST` | `/api/v1/send`             | Send a summary via email (legacy sync)                |
| `POST` | `/api/v1/analyze-and-send` | All-in-one: upload → analyze → email (sync)           |
| `POST` | `/api/v1/stream`           | SSE stream: real-time pipeline progress               |

All endpoints except `/health` and docs require the `X-API-Key` header.

---

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) triggers on PRs to `main`:

```
Backend CI                    Frontend CI
───────────                   ───────────
✓ Python 3.12 setup           ✓ Node 20 setup
✓ pip install                 ✓ npm ci
✓ Ruff lint + format          ✓ ESLint
✓ pip-audit                   ✓ TypeScript check
✓ pytest                      ✓ Next.js build
✓ Docker build                ✓ npm audit
                              ✓ Docker build

         Docker Compose Integration
         ───────────────────────────
         ✓ Build all services
         ✓ Verify images created
```

---

## Deployment

| Service      | Platform | Live URL                                               |
| ------------ | -------- | ------------------------------------------------------ |
| Frontend     | Vercel   | https://sales-insight-automator-red.vercel.app         |
| Backend API  | Render   | https://sales-insight-automator-ds0d.onrender.com      |
| Swagger Docs | Render   | https://sales-insight-automator-ds0d.onrender.com/docs |

### Frontend → Vercel

1. Push to GitHub
2. Import repo in [vercel.com](https://vercel.com)
3. Set root directory to `frontend`
4. Add environment variables: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_API_KEY`
5. Deploy

### Backend → Render

1. Push to GitHub
2. Create a new Web Service in [render.com](https://render.com)
3. Set root directory to `backend`, runtime: **Docker**
4. Add all environment variables from `.env.example`
5. Deploy

---

## Environment Variables

### Backend (`backend/.env`)

| Variable                | Required        | Description                                         |
| ----------------------- | --------------- | --------------------------------------------------- |
| `API_KEY`               | ✅              | Secret for API authentication                       |
| `ALLOWED_ORIGINS`       | ✅              | Comma-separated CORS origins                        |
| `LLM_PROVIDER`          | ✅              | Primary LLM — `gemini` or `groq`                    |
| `LLM_FALLBACK_PROVIDER` | ❌              | Fallback LLM — `groq` or `gemini` (default: `groq`) |
| `GEMINI_API_KEY`        | If using Gemini | Google AI Studio API key                            |
| `GROQ_API_KEY`          | If using Groq   | Groq Cloud API key                                  |
| `RESEND_API_KEY`        | ✅              | Resend email service API key                        |
| `FROM_EMAIL`            | ❌              | Sender address (default: `onboarding@resend.dev`)   |
| `SMTP_HOST`             | ❌              | SMTP fallback host (blank = disabled)               |
| `SMTP_PORT`             | ❌              | SMTP port (default: 587)                            |
| `SMTP_USER`             | ❌              | SMTP username                                       |
| `SMTP_PASSWORD`         | ❌              | SMTP password                                       |
| `REDIS_URL`             | ❌              | Redis URL (blank = sync fallback)                   |
| `DATABASE_URL`          | ❌              | SQLite path (default: `sqlite:///jobs.db`)          |
| `CHART_DIR`             | ❌              | Chart output dir (default: `charts`)                |
| `MAX_UPLOAD_SIZE_MB`    | ❌              | Max file size in MB (default: 50)                   |
| `MAX_ROWS`              | ❌              | Max rows to process (default: 100,000)              |
| `RATE_LIMIT`            | ❌              | Rate limit string (default: `10/minute`)            |
| `UPLOAD_RATE_LIMIT`     | ❌              | Upload rate limit (default: `10/minute`)            |

### Frontend (`frontend/.env.local`)

| Variable              | Required | Description                              |
| --------------------- | -------- | ---------------------------------------- |
| `NEXT_PUBLIC_API_URL` | ✅       | Backend API base URL                     |
| `NEXT_PUBLIC_API_KEY` | ✅       | API key (must match backend's `API_KEY`) |

---

## Project Structure

```
sales-insight-automator/
├── frontend/
│   ├── app/
│   │   ├── layout.tsx            ← Root layout + metadata
│   │   ├── page.tsx              ← Main SPA (upload flow)
│   │   └── globals.css           ← Tailwind + custom styles
│   ├── components/
│   │   ├── drop-zone.tsx         ← Drag & drop file upload
│   │   ├── email-input.tsx       ← Validated email field
│   │   ├── subject-editor.tsx    ← Editable subject line
│   │   ├── file-preview.tsx      ← Client-side CSV preview
│   │   ├── progress-tracker.tsx  ← Multi-step progress indicator
│   │   ├── summary-preview.tsx   ← Markdown summary renderer
│   │   ├── theme-toggle.tsx      ← Dark/light mode switch
│   │   └── history-sidebar.tsx   ← Upload history (localStorage)
│   ├── lib/
│   │   ├── api.ts                ← API client + SSE handler
│   │   ├── validators.ts         ← Client-side validation
│   │   └── utils.ts              ← Utility functions
│   ├── Dockerfile                ← Multi-stage (~80MB)
│   ├── .env.example
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py               ← FastAPI entry + lifespan + structured logging
│   │   ├── config.py             ← Pydantic Settings (Redis, SMTP, LLM fallback)
│   │   ├── database.py           ← SQLite job persistence layer
│   │   ├── logging_config.py     ← Structured JSON logging with job_id context
│   │   ├── worker.py             ← Redis queue consumer (background process)
│   │   ├── middleware/
│   │   │   ├── auth.py           ← API key verification
│   │   │   ├── rate_limit.py     ← slowapi rate limiter
│   │   │   └── security_headers.py ← HSTS, X-Frame, etc.
│   │   ├── routers/
│   │   │   ├── health.py         ← Health check (Redis + DB connectivity)
│   │   │   └── upload.py         ← Async upload, job status, send, stream
│   │   ├── services/
│   │   │   ├── parser.py         ← CSV/XLSX parsing + sanitization
│   │   │   ├── analyzer_v2.py    ← Enhanced analytics (vectorized Pandas)
│   │   │   ├── charts.py         ← matplotlib chart generation (3 PNGs)
│   │   │   ├── llm_v2.py         ← Structured JSON LLM + primary/fallback + retry
│   │   │   └── mailer_v2.py      ← HTML email + inline charts + SMTP fallback
│   │   └── schemas/
│   │       └── models.py         ← Pydantic request/response models v2
│   ├── tests/
│   │   ├── test_parser.py        ← Parser unit tests
│   │   ├── test_analyzer.py      ← Analyzer v1 unit tests
│   │   ├── test_analyzer_v2.py   ← Analyzer v2 unit tests
│   │   ├── test_database.py      ← SQLite job DB tests
│   │   ├── test_api.py           ← API v1 integration tests
│   │   └── test_api_v2.py        ← API v2 integration tests (jobs, health)
│   ├── Dockerfile                ← Multi-stage + matplotlib deps (~180MB)
│   ├── .env.example
│   └── requirements.txt
│
├── scripts/
│   └── smoke_test.py            ← End-to-end smoke test script
├── docker-compose.yml            ← Redis + API + Worker + Frontend
├── .github/workflows/ci.yml     ← CI pipeline
├── sales_q1_2026.csv            ← Reference test data
├── .gitignore
└── README.md                    ← You are here
```

---

## Tech Stack

| Layer          | Technology                                     |
| -------------- | ---------------------------------------------- |
| **Frontend**   | Next.js 15, React 18, TypeScript, Tailwind CSS |
| **Backend**    | FastAPI, Python 3.12+, Pydantic v2             |
| **AI**         | Google Gemini 2.0 Flash / Groq Llama 3.3 70B   |
| **Email**      | Resend API (primary) + SMTP (fallback)         |
| **Data**       | Pandas, NumPy, openpyxl                        |
| **Charts**     | matplotlib (headless Agg backend)              |
| **Queue**      | Redis (optional — graceful sync fallback)      |
| **Database**   | SQLite (job persistence)                       |
| **Auth**       | API Key (X-API-Key header)                     |
| **Rate Limit** | slowapi                                        |
| **Logging**    | Structured JSON (stdlib logging)               |
| **Container**  | Docker, Docker Compose                         |
| **CI/CD**      | GitHub Actions                                 |
| **Hosting**    | Vercel (frontend), Render (backend)            |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <p><strong>Built with 💜 by Rabbitt AI Engineering</strong></p>
  <p><sub>Sales Insight Automator v2.0.0 — turning raw data into strategic gold.</sub></p>
</div>
