# Consultation Notes App — Project Context & Progress

_Last updated: this session — Patient Email/WhatsApp send feature merged to `dev`,
vitals-in-email prompt fix merged, WSL Node.js environment fixed_

## 1. What this is
AI-powered consultation notes tool — doctor types patient visit notes, AI streams back
3 sections: summary for doctor's records, next steps, and a patient-friendly email draft.
Doctors can now send the patient-facing draft directly via Gmail or WhatsApp, or copy it,
without leaving the app. This is being built as a **new product under DeepAKAI's
multi-product suite** (alongside the existing WhatsApp bot business) — designed to
eventually serve other business verticals too (salons, restaurants, CA firms), not just
doctors.

Repo: https://github.com/DpkMaurya1990/ai-healthcare-consultation-saas

## 2. Tech stack
- Frontend: Next.js 16.1.6 (Turbopack, static export, `output: 'export'`), Clerk auth
  (`@clerk/nextjs` ^6.39.0), ReactMarkdown, react-datepicker,
  `@microsoft/fetch-event-source` for SSE streaming
- Backend: FastAPI, `fastapi-clerk-auth` (JWT via JWKS), OpenAI (`gpt-5-nano` in prod) /
  Groq (dev/testing, via OpenAI-compatible endpoint), SSE streaming
- Deployment: single combined Docker container (FastAPI serves both API + static frontend)
- Current live auto-deploy: **Hugging Face Spaces**, via GitHub Actions workflow
  (`.github/workflows/deploy-hf.yml`) triggered on push to `main`/`dev`
- Planned: Supabase Postgres (Phase 4), Railway hosting → AWS App Runner later (Phase 5)

**Locked architectural decision**: single-container FastAPI + static Next.js export is
the permanent model. Vercel+Render split is fully abandoned.

## 3. Folder structure
```
ai-healthcare-consultation-saas/
├── Dockerfile                  # combined build: Next.js static export + FastAPI, EXPOSE 7860
│                                #   ARG/ENV for NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY and
│                                #   NEXT_PUBLIC_API_URL (build-time bake)
├── backend/
│   ├── main.py                  # FastAPI app, /api/v1 routes, Clerk auth, OpenAI/Groq streaming,
│   │                            #   catch-all static route (serves Next.js pages like
│   │                            #   /product -> product.html). System prompt now instructs
│   │                            #   AI to carry patient vitals (BP, temp, etc.) into the
│   │                            #   patient email section in plain language (this session)
│   ├── requirements.txt
│   ├── .env                     # gitignored — CLERK_SECRET_KEY, CLERK_JWKS_URL, OPENAI_API_KEY,
│   │                            #   AI_PROVIDER, GROQ_API_KEY
│   └── cons_app_venv/           # gitignored — Python 3.12.3 virtual environment (WSL)
├── pages/
│   ├── index.tsx                 # landing page
│   ├── product.tsx               # consultation notes form + streaming output.
│   │                             #   NEW this session: optional Patient Email / Patient
│   │                             #   Phone fields, Send via Gmail / Send via WhatsApp /
│   │                             #   Copy buttons, long-draft warning (see Section 5)
│   ├── sign-in.tsx               # dedicated Clerk <SignIn routing="path" path="/sign-in" />
│   └── _app.tsx                  # ClerkProvider — publishableKey + fallback redirect URLs
├── next.config.ts               # output: 'export'
├── package.json                 # package-lock.json regenerated this session under
│                                 #   Linux-native npm (see Section 6)
├── eslint.config.mjs
├── Consultation_Notes_App.md    # this file — project context & progress tracker
├── .env.local                   # gitignored — NEXT_PUBLIC_API_URL (kept EMPTY),
│                                 #   NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
└── .gitignore                   # includes backend/cons_app_venv/, .env*, .env.local, __pycache__/
```

## 4. Repo / branch reality check
- **Remote branches**: `main` and `dev` only (feature branches created off `dev` per
  task, deleted after merge)
- **This session's branch**: `feature/patient-contact-fields` — created off `dev`,
  merged back into `dev` via PR, then deleted (GitHub offered safe-delete after merge)
- **`main` branch auto-deploys to Hugging Face Spaces on every push** via GitHub Actions —
  merging to `main` is a live production deploy. Local Docker testing before any future
  merge to `main` remains critical.
- **PR #1 (`dev` → `main`)**: still open from earlier sessions, not addressed this
  session — separate item, tracked in Section 13.

## 5. Current status (as of this session)
**Branch**: `dev` (local synced after merge of `feature/patient-contact-fields`)

### Local workflow notes added this session
- [x] Added a portable local helper script at [scripts/dev.sh](scripts/dev.sh) with `start`, `stop`, and `rebuild` commands.
- [x] Updated [README.md](README.md) to make the `Local Runbook` the single canonical source for local backend start/stop/rebuild steps.
- [x] Made `scripts/dev.sh` executable so the shorter `./scripts/dev.sh ...` form works alongside `bash scripts/dev.sh ...`.

**Phase 1 — Stabilize deployment**: ✅ Complete (prior session)

**This session's feature — Patient Email/WhatsApp send + vitals fix**: ✅ **COMPLETE,
MERGED TO `dev`**

### What was built
- [x] Optional `Patient Email` and `Patient Phone` fields added to the consultation form
  (deliberately **not required** — doctors who only need the AI summary for their own
  records shouldn't be blocked from submitting)
- [x] **Send via Gmail** button — always visible regardless of whether email is filled.
  Uses a `mail.google.com` compose deep-link (`URLSearchParams` for safe encoding). If
  `patientEmail` is empty, the `to=` parameter is omitted entirely (not sent as empty
  string) so Gmail opens with "To" blank and the doctor can pick from Gmail's own
  contacts — covers the case where the doctor forgot to enter the email but has
  messaged the patient before.
- [x] **Send via WhatsApp** button — only rendered when `patientPhone` is filled, since
  the `wa.me/<number>` deep-link format requires the number to be part of the URL path
  (no equivalent "leave blank, pick from contacts" option exists for WhatsApp deep-links).
- [x] **Copy** button — uses `navigator.clipboard.writeText()` (the secure, standard
  clipboard API — deliberately not a manual selection/`execCommand` approach, per
  pastejacking-prevention best practice).
- [x] **Content scoping (important privacy/liability decision)** — Send/Copy actions
  extract *only* the "Draft of email to patient" section from the AI output via a
  regex marker (`### Draft of email to patient...`), and further split out the
  AI-generated `Subject:` line into the actual email subject field. The doctor's
  internal "Summary of visit" and "Next steps" sections are **never** included in
  anything sent to or copied for the patient — this was caught and fixed after initial
  testing showed the full 3-section output going out via Gmail/WhatsApp.
- [x] **Long-draft warning** — if the extracted draft exceeds 1500 characters, an amber
  warning is shown recommending the Copy button, since Gmail/WhatsApp deep-links have
  practical (non-fixed, platform-dependent) URL length limits. Deliberately **not**
  capping AI generation length to fit URL limits — that risked truncating genuine
  medical content; the warning + Copy fallback approach was chosen instead.
- [x] **Backend prompt fix** — patient vitals (BP, temperature, weight, height, age,
  pulse, etc.) mentioned in the doctor's notes were appearing in the doctor's summary
  but being silently dropped from the patient email. Fixed via an explicit instruction
  added to `system_prompt` in `backend/main.py`: vitals must also appear in the patient
  email, phrased in plain language with context (e.g. "your blood pressure was 120/80,
  which is within the normal range" rather than raw "BP 120/80"). Verified working via
  Docker test — both BP and temperature now appear correctly with context in the email.
- [x] Verified end-to-end via full Docker build + `docker run` (production-matching
  build path) — not via `next dev`, see known issue below.
- [x] PR `feature/patient-contact-fields` → `dev` raised and **merged**
- [x] `package-lock.json` updated as a side effect of reinstalling dependencies under
  Linux-native npm this session (see Section 6) — committed as part of the same PR,
  confirmed as an expected/legitimate change, not a conflict

### Known open bug fixed mid-session
**JSX syntax error caught by Docker build**: initial implementation of the Gmail/WhatsApp
`<a>` tags was missing the opening `<a` tag (attributes like `href`, `target` were typed
directly without an enclosing tag) — a copy-paste slip. This caused `npm run build` to
fail inside the Docker build step with `Type error: Unexpected token`. This is a good
example of why local Docker build verification (which runs the real `next build`/
TypeScript check) catches issues that manual code review alone might miss. Fixed by
adding the missing `<a` in both locations.

### Backlog item (deferred, low priority, not blocking)
- **Visit date in patient email shows raw ISO format** (e.g. `2026-07-17`) instead of
  human-readable format (e.g. `July 17, 2026`). Doctor confirmed this looks slightly
  mechanical in the generated email. Planned fix: add an instruction to the system
  prompt telling the AI to render the date in natural language. Not done this session —
  explicitly deferred to keep scope tight; tracked here for the next prompt-engineering
  pass (could be bundled with any future system-prompt work, e.g. the date-formatting
  fix could be combined with the PII redaction prompt changes in Phase 2).

## 6. Development environment
- **WSL location**: `~/ai-healthcare-consultation-saas` (Linux-native filesystem)
- **Python**: 3.12.3, at `/usr/bin/python3`
- **Virtual env name**: `cons_app_venv` (inside `backend/`, gitignored)
- **VS Code**: connected via WSL extension

**NEW this session — Node.js/npm was not previously set up natively in WSL.** Until now,
all frontend builds happened only inside Docker (which has its own isolated Node.js in
the image), so this gap was never surfaced. First attempt to run `npm run dev` locally
in WSL resolved to the **Windows-side npm** (`/mnt/c/Program Files/nodejs/npm`, inherited
via WSL's default Windows `PATH` passthrough), which cannot handle WSL's Linux filesystem
paths (`UNC paths are not supported` error). 

**Fix applied**: installed `nvm` (Node Version Manager) natively inside WSL, then
`nvm install --lts` (resolved to Node v24.18.0). `which npm` now correctly resolves to
`/home/deepa/.nvm/versions/node/v24.18.0/bin/npm`. This is now the standard local Node
setup going forward — **do not use Windows-side Node/npm from within WSL**.

**`.env` files (gitignored, must be manually recreated in any fresh clone/environment)**:
- Root `.env.local` (frontend): `NEXT_PUBLIC_API_URL` (**keep this EMPTY**),
  `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY`
- `backend/.env` (backend): `CLERK_SECRET_KEY`, `CLERK_JWKS_URL`, `OPENAI_API_KEY`,
  `AI_PROVIDER`, `GROQ_API_KEY`

**Docker build command** (standard going forward):
```bash
docker build -t consultation-app-test:latest \
  --build-arg NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=$(grep NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY .env.local | cut -d '=' -f2) \
  --build-arg NEXT_PUBLIC_API_URL=$(grep NEXT_PUBLIC_API_URL .env.local | cut -d '=' -f2) \
  .

docker run -p 7860:7860 --env-file backend/.env -e ALLOWED_ORIGINS=http://localhost:7860 consultation-app-test
```

**Recurring operational pattern this session**: multiple `docker run` attempts failed
with `port is already allocated` because a previous test container (from an earlier
session, sometimes over a day old) was still running in the background — Docker
containers survive across WSL/laptop sessions unless explicitly stopped. **Always run
`docker ps` before `docker run`** and `docker stop <name>` any container already bound
to port 7860. Several stray exited containers have also accumulated from repeated test
runs (harmless, but `docker container prune` can clean these up once no active testing
is in progress — only removes stopped containers, never running ones).

### Known open issue — `next dev` broken (NOT a regression from this session's code)
Running `npm run dev` (Next.js 16.1.6, Turbopack) fails with:
```
⨯ Middleware cannot be used with "output: export". See more info here: https://nextjs.org/docs/advanced-features/static-html-export
```
Confirmed **no `middleware.ts`/`.js` file exists anywhere in the source tree** — the only
matches are Next.js's own auto-generated `.next/dev/server/middleware.js`. This appears
to be Clerk's SDK internally registering middleware-like behavior that Next.js 16's dev
server detects and rejects under static export mode — a known, long-standing Next.js
limitation (`output: 'export'` + Middleware are fundamentally incompatible by design;
confirmed via Next.js's own GitHub issue history). 

**Critically: this only affects `next dev`.** Production builds (`next build`, which is
what Docker/Hugging Face actually run) are unaffected — confirmed by this session's
successful Docker builds. **Local frontend verification must go through the Docker
build+run path, not `npm run dev`, until this is investigated further.** Scoped as a
separate backlog item, not blocking any current work (see Section 13).

## 7. AI provider strategy
No changes this session. Still:
- **Dev/testing**: Groq (`AI_PROVIDER=groq`), OpenAI-compatible endpoint, model defaults
  to `llama-3.3-70b-versatile` via `GROQ_MODEL`
- **Production**: OpenAI (`AI_PROVIDER=openai` or unset — default), model `gpt-5-nano`
- **Caveat**: Groq is for testing plumbing/streaming/UI flow only — output quality must
  still be validated against OpenAI before shipping prompt changes to production.

## 8. Full roadmap (locked order)
1. **Phase 1 — Stabilize deployment** ✅ **COMPLETE**
2. **Patient Email/WhatsApp send feature** ✅ **COMPLETE** (this session, see Section 5)
3. **Phase 2 — Security & compliance** (priority order locked — see Section 9) — **next up**
4. **Phase 3 — Multi-tenant redesign**
   - Hardcoded doctor-only system prompt → `business_type` template system
   - Clerk Organizations for tenant scoping (`org_id` JWT claim)
   - Every API request must explicitly verify `org_id` against DB row (defense in depth)
5. **Phase 4 — Data & billing**
   - Supabase Postgres: consultation history, usage tracking, plan gating
   - Wire up `Protect`/`PricingTable` (removed as dead code in Phase 1)
   - Per-tenant Row Level Security (RLS) + encryption at rest, including encrypted backups
     with audit-logged backup access
   - Data retention & deletion policy (DPDP Act purpose-limitation) — currently undefined
6. **Phase 5 — Hosting & launch**
   - Deploy combined container to Railway first
   - Custom domain: `notes.deepakai.in` (or similar subdomain)
   - Migrate to AWS App Runner later if traffic/tenant count grows
   - Soft launch to 1-2 existing clients before wider rollout

**Explicitly deferred**: tenant-specific subdomains, native mobile app build itself.
Backend auth design (stateless Clerk JWT) is already mobile-compatible by design.

## 9. Security implementation order (locked)
Given this is public-facing health data under India's DPDP Act, Phase 2 priority order:

1. **PII redaction before OpenAI/Groq call** — highest risk. Patient name + notes
   currently sent with zero redaction. **Approach agreed this session**: hybrid of (a)
   structured-field isolation — patient name is already a separate form field, so
   token-replace it (`[PATIENT_NAME]`) before the LLM call and substitute back in the
   response, rather than sending it raw; (b) lightweight, deterministic regex redaction
   for free-text notes covering phone numbers, email addresses, dates of birth, and
   ID-number-like patterns. NER-based redaction (e.g. Microsoft Presidio) was evaluated
   and explicitly deferred to Phase 3/4 — too much infra weight (image size, cold start)
   for the current single-container, pre-launch stage. OpenAI's zero-data-retention
   enterprise tier was also evaluated and deferred — doesn't satisfy DPDP's data
   minimization principle on its own and isn't practically accessible pre-launch.
   **Implementation not started yet** — this is the next scheduled piece of work.
   - **Known engineering risk flagged for implementation**: SSE streaming sends AI output
     token-by-token, so a placeholder like `[PATIENT_NAME]` could be split across chunk
     boundaries. Plan: a small buffering layer in the backend that holds only as much
     text as needed to safely detect a complete/incomplete placeholder before flushing to
     the frontend, to avoid broken placeholder text appearing mid-stream.
   - **Decision needed/confirm before implementation**: token map (placeholder → real
     value) will be held purely in-memory, request-scoped (Python dict), never persisted
     to disk/DB/logs — consistent with the existing audit-logging rule (metadata only).
2. **Rate limiting** — per-user + per-IP (e.g. via `slowapi`), plus per-tenant daily
   token/request caps (ties into Phase 4 billing).
3. **Input validation + prompt injection guard** — clearly delimited/escaped user-content
   block; plus max-length validation on the notes field. Regex used here (and in PII
   redaction above) must avoid catastrophic-backtracking patterns (ReDoS) — use simple,
   bounded patterns, no nested quantifiers; this was explicitly checked for the regexes
   already shipped this session (WhatsApp phone-digit stripping, patient-email-section
   marker extraction) and both are simple/bounded/safe.
4. **Audit logging (metadata only)** — structured logs (request_id, user_id, org_id,
   timestamp, action). Patient PII must never enter logs.
5. **Remaining items** (RLS, data retention policy, infra hardening — HTTPS enforcement,
   security headers CSP/HSTS/X-Frame-Options, non-root Docker user, minimal base image,
   dependency audits, incident response readiness) — picked up in Phase 2 (infra) and
   Phase 4 (RLS/retention).

**Also flagged (not yet scheduled)**:
- ReactMarkdown rendering AI output — confirm it sanitizes by default to avoid XSS
- Frontend static export bakes `NEXT_PUBLIC_*` env vars at build time — always verify
  build-time env vars are correctly passed via `--build-arg`
- **NEW this session (from external security checklist review)**: explicit audit item —
  verify no *secret* env var (`OPENAI_API_KEY`, `CLERK_SECRET_KEY`, `GROQ_API_KEY`) ever
  gets a `NEXT_PUBLIC_`/`VITE_`-style prefix that would bake it into the public frontend
  bundle. Currently confirmed correctly separated (`backend/.env`, non-prefixed) — this
  is a recurring check to repeat whenever new env vars are added, not a current bug.

## 10. Observability plan (locked, unchanged)
1. **Langfuse** — next up (LLM cost + prompt debugging).
2. **Sentry** — Phase 2, alongside security work.
3. **Prometheus + Grafana** — deferred to Phase 4/5.

## 11. Security concerns to actively track
- **PII to OpenAI/Groq**: zero redaction currently. Phase 2, item 1 — approach agreed,
  not yet implemented (see Section 9).
- **No rate limiting** on `/api/v1/consultation`.
- **No audit trail / logging** of consultation data access.
- **Secrets**: all confirmed gitignored (`.env`, `.env.local`). Production should move to
  a proper secrets manager (Railway/AWS built-in, or AWS Secrets Manager at App Runner
  stage) rather than plain `.env` files in the container.
- **No input length limits** on the notes field — also relevant to the "Long Input DoS"
  pattern flagged in a general security checklist reviewed this session; principle
  already tracked here, implementation still pending.
- **Data at rest** (Phase 4, once Supabase DB added): needs encryption at rest + RLS.
- **CORS**: fixed in Phase 1 (env-var driven), revisit allowed origins once custom domain
  is finalized in Phase 5.
- **Multi-tenant leakage risk** (Phase 3 forward-look): `org_id` claim must be explicitly
  checked against DB row on every request once multi-tenancy is introduced.
- **Clerk `<SignIn routing="path" />` sub-routes** (`/sign-in/factor-one`,
  `/sign-in/sso-callback`, etc.) — the static catch-all route in `main.py` cannot resolve
  these on a direct page load/refresh. Not currently broken in normal use, but worth a
  specific functional test if MFA or SSO is exercised in the future.
- **NEW this session — patient contact info handling**: `patientEmail`/`patientPhone`
  are deliberately **client-side only** — never included in the `/api/v1/consultation`
  request body, never sent to the LLM, never logged. Only `patient_name`,
  `date_of_visit`, and `notes` are sent to the backend, unchanged from before this
  session. This keeps the new contact fields outside the scope of the PII-redaction work
  in Section 9 (which concerns data sent to the LLM), but they should still be considered
  in scope for a future "no PII in logs" audit once contact fields are ever persisted
  (Phase 4, Supabase).
- **Clipboard API usage confirmed secure**: Copy button uses
  `navigator.clipboard.writeText()` rather than a manual selection-based or
  `document.execCommand('copy')` approach, consistent with pastejacking-prevention
  guidance reviewed this session.

## 12. Working rules with Claude (unchanged, reconfirmed this session)
1. **Sandwich format** for all code changes — surrounding context, old code, new code.
2. **File name/path always stated** alongside every diff. New files: exact folder location.
3. **1–2 micro-steps at a time** — never dump all steps or batch large changes.
4. **No grep/find commands given to Deepak to run himself** — Claude inspects internally,
   tells Deepak "file X mein section Y dhundo" instead.
5. **Always state the purpose** of any code or command before/alongside giving it.
6. **Hinglish** for all communication; **simple English only for website-facing content**
   — reconfirmed this session after a warning message was initially drafted in Hinglish
   and corrected to English, since it's user-facing UI copy, not chat communication.
7. **Always specify git branch** before any commit instruction.
8. **PRs/pushes go to `dev` first**, then `dev` → `main`. Never direct to `main`. Pushing
   to `main` triggers an automatic live deploy to Hugging Face Spaces via GitHub Actions.
9. **Deep business thinking expected** — not just code generation.
10. **Claude provides code/content in chat, does not create/save repo code files
    directly** — Deepak creates and saves those himself.
11. **If Deepak is unsure about code placement**, he pastes the snippet for Claude to
    verify correctness before proceeding.
12. **This progress file is a living document** — regenerated in full whenever requested.
13. **Exception for this file specifically**: `Consultation_Notes_App.md` IS created/
    delivered by Claude as an actual downloadable file, since Deepak downloads and
    re-uploads it to project resources for context continuity across new chat sessions.
14. GitHub Personal Access Tokens (classic, `ghp_...` prefix) require the explicit
    **`workflow` scope** to push changes to any file under `.github/workflows/`.
15. **NEW learning from this session**: when working changes accidentally land directly
    on `dev` (uncommitted), they can be safely moved to a proper feature branch with
    `git checkout -b <branch-name>` *before* committing — this carries the uncommitted
    working-directory changes to the new branch and leaves `dev` untouched. Always
    double-check `git status` shows the correct branch immediately before the first
    `git add`/`git commit` of any task.

## 13. Next immediate steps (as of end of this session)

**Patient Email/WhatsApp send feature is fully closed and merged to `dev`.** Small
cleanup items remain, then Phase 2 begins:

- [ ] (Optional, low priority) Address the still-open PR #1 (`dev` → `main`) — verify
  its current state before deciding next action.
- [ ] (Backlog, low priority) Fix visit date formatting in patient email — raw ISO
  (`2026-07-17`) → human-readable (`July 17, 2026`) via a system prompt instruction
  (see Section 5).
- [ ] (Backlog, investigate when time allows) `next dev` broken under Next.js 16 +
  Clerk + `output: 'export'` — not blocking (Docker build/run works fine as the
  verification path), but worth a root-cause pass eventually for faster local iteration
  without full Docker rebuilds each time (see Section 6).
- [ ] Begin **Langfuse integration** (observability — Section 10, item 1)
- [ ] Begin **Phase 2 — Security & Compliance**, starting with **PII redaction before
  OpenAI/Groq calls** (Section 9, item 1) — approach already agreed (structured-field
  isolation + lightweight regex + streaming-safe buffered detokenizer), implementation
  not yet started. This remains the single highest legal/business risk item.

**Recommended starting point for next session**: PII redaction implementation —
starting with patient-name token substitution (simplest, highest-impact first step),
then free-text regex redaction, then the streaming-safe buffering layer.
