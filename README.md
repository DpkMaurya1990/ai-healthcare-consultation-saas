---
title: AI Healthcare Consultation SaaS
emoji: 🏥
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

# 🏥 AI Healthcare Consultation SaaS (GenAI + Streaming)

🚀 A production-style **Generative AI SaaS application** that transforms doctor consultation notes into structured summaries with real-time streaming responses — doctor summary, next steps, and a patient-friendly email draft.

---

## ⚡ Key Features
* 🔐 Secure authentication using Clerk (JWT-based)
* 🧠 AI-powered consultation summary generation (OpenAI in production, Groq for dev/testing)
* ⚡ Real-time streaming responses (SSE)
* 📄 Structured output:
  * Summary for doctor's records
  * Next steps
  * Patient-friendly email draft

---

## 🧠 How It Works
```text
User → Login (Clerk)
     → Enter Notes (Next.js frontend)
     → API Call (FastAPI backend, same container)
     → OpenAI / Groq Streaming Response
     → Live Output Rendered (ReactMarkdown)
```

---

## 🛠️ Tech Stack
### Frontend
* Next.js (static export)
* ReactMarkdown (render AI output)
* Clerk (authentication)
* fetch-event-source (SSE streaming)

### Backend
* FastAPI
* OpenAI API / Groq API (streaming, switchable via `AI_PROVIDER`)
* Clerk JWT verification
* Uvicorn (ASGI server)

### Deployment
* **Single combined Docker container** — FastAPI serves both the API and the static Next.js frontend
* Current auto-deploy target: **Hugging Face Spaces** (via GitHub Actions on push to `main`/`dev`)
* Planned: Railway (initial hosting), AWS App Runner (scale)

---

## 📂 Project Structure
```bash
.
├── Dockerfile              # combined build: Next.js static export + FastAPI
├── backend/
│   ├── main.py              # FastAPI app, /api/v1 routes, Clerk auth, OpenAI/Groq streaming
│   └── requirements.txt
├── pages/
│   ├── index.tsx
│   └── product.tsx
├── next.config.ts           # output: 'export'
└── README.md
```

---

## 🚀 Getting Started (Local Setup)

### 1️⃣ Backend Setup
📍 Run inside `backend/`
```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2️⃣ Frontend Setup
📍 Run inside project root
```bash
npm install
npm run dev
```

### 3️⃣ Full Docker Build (recommended, matches production)
📍 Run from project root
```bash
docker build -t consultation-app-test:latest \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=<your_key> \
  --build-arg NEXT_PUBLIC_API_URL= \
  .

docker run -p 7860:7860 --env-file backend/.env -e ALLOWED_ORIGINS=http://localhost:7860 consultation-app-test
```

---

## 🔐 Environment Variables

### Frontend (root `.env.local`)
```env
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
NEXT_PUBLIC_API_URL=
```
> Leave `NEXT_PUBLIC_API_URL` empty for same-origin relative API calls (works for both local Docker and production, since frontend and backend are served from the same container/domain).

### Backend (`backend/.env`)
```env
CLERK_SECRET_KEY=your_clerk_secret_key
CLERK_JWKS_URL=your_clerk_jwks_url
OPENAI_API_KEY=your_openai_key
AI_PROVIDER=openai   # or 'groq' for dev/testing
GROQ_API_KEY=your_groq_key
```

---

## 🧪 API Endpoints
* `GET /health` → Health check
* `POST /api/v1/consultation` → Generate AI summary (SSE streaming)

---

## 🚀 Roadmap
1. **Phase 1 — Stabilize deployment** ✅
2. **Phase 2 — Security & compliance** (PII redaction, rate limiting, input validation, audit logging)
3. **Phase 3 — Multi-tenant redesign** (business-type templates, Clerk Organizations)
4. **Phase 4 — Data & billing** (Supabase Postgres, plan gating, RLS)
5. **Phase 5 — Hosting & launch** (Railway → AWS App Runner, custom domain)

---

## 🧠 Author
**Deepak Maurya**
Founder, DeepAKAI

---

## ⭐ If you found this useful
Give it a ⭐ on GitHub!