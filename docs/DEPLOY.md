# Deployment & Pre-Launch Verification Guide

This guide covers deploying the **FastAPI backend** (Render) and **Next.js 15 frontend** (Vercel), along with verified footprint/memory constraints and a mobile/incognito smoke checklist.

---

## 1. Backend Environment Variables (Render)

Configured in [`backend/render.yaml`](../backend/render.yaml) and [`backend/.env.example`](../backend/.env.example):

| Variable | Value / Example | Required | Notes |
| :--- | :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Yes | Matches `backend/Dockerfile` (`python:3.11-slim`). |
| `CORS_ORIGINS` | `https://frontend-tau-murex-6pqd8vtg90.vercel.app` | Yes (Prod) | Comma-separated allowed origins. Never uses wildcard `*`. When unset locally, defaults strictly to `http://localhost:3000,http://127.0.0.1:3000`. |
| `ALLOW_ORIGIN_REGEX` | `^https://frontend-[a-z0-9-]+\.vercel\.app$` | Optional | Restrict preview origins strictly to your Vercel project's preview deployments. |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Optional | Set `sync: false` in Render Dashboard. When unset, cloud opt-in endpoints fail closed/fallback to local heuristic extraction; `/api/chat` returns HTTP `503`. |
| `OPENROUTER_PRIMARY_MODEL` | `mistralai/mistral-small-3.2-24b-instruct` | Optional | Default single primary extraction slug (chain: primary $\to$ local heuristic). |
| `OPENROUTER_CHAT_MODEL` | `mistralai/mistral-small-3.2-24b-instruct` | Optional | Default primary chat slug. |

### Render Deployment Steps
1. Create a **New Web Service** on Render pointing to this repository, with **Root Directory** = `backend` (or apply the `render.yaml` blueprint).
2. **Build Command:** `pip install -r requirements.txt`
3. **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT` (single worker; do **not** increase `WEB_CONCURRENCY` on 512 MB instances).
4. Add `CORS_ORIGINS`, optional `ALLOW_ORIGIN_REGEX`, and `OPENROUTER_API_KEY` in Render **Environment** settings.
5. Verify health endpoint after deploy: `GET https://<your-render-service>.onrender.com/api/health` returns `{"status": "healthy", ...}`.

---

## 2. Frontend Environment Variables (Vercel)

Configured via [`frontend/src/config/api.ts`](../frontend/src/config/api.ts):

| Variable | Value / Example | Required | Notes |
| :--- | :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `https://<your-render-service>.onrender.com` | Yes (Prod) | No trailing slash. In production builds (`NODE_ENV === "production"`), missing `NEXT_PUBLIC_API_URL` does **not** fall back to `127.0.0.1`; the UI shows an explicit backend-unreachable / config notice. |

### Vercel Deployment Steps
1. Import the repository on Vercel and set **Root Directory** to `frontend`.
2. Add `NEXT_PUBLIC_API_URL=https://<your-render-service>.onrender.com` for **Production** (and **Preview** if testing against staging/Render).
3. Trigger a fresh Vercel deployment after setting `NEXT_PUBLIC_API_URL` (Next.js inlines `NEXT_PUBLIC_*` at build time).

---

## 3. Dependency Footprint & Memory Risk (512 MB Free-Tier Check)

Measured locally on Windows Python (`pip install --no-cache-dir --ignore-installed --target` with [`backend/requirements.txt`](../backend/requirements.txt)) and `K32GetProcessMemoryInfo` (`rss_mb` / `peak_rss_mb` / `private_mb`):

- **Clean requirements footprint on disk:** **335.14 MB** (`opencv-python`, `onnxruntime`, `rapidocr-onnxruntime`, `numpy`, `pillow`, `pdfminer.six`, `pypdfium2`, etc.).
- **Idle FastAPI app (`/api/health`):** `74.27 MB` RSS (`74.32 MB` peak RSS, `61.56 MB` private commit).
- **After 1 digital PDF (`01_dr_lal_healthy_adult.pdf`, 2,910 bytes):** `76.03 MB` RSS (`76.12 MB` peak RSS, `63.22 MB` private commit).
- **After 1 phone photo (`09_phone_photo_cbc_skewed.jpg`, 33,632 bytes — initializes RapidOCR ONNX sessions):** `149.18 MB` RSS, **`246.30 MB` peak RSS**, **`341.70 MB` private commit**.
- **Synthetic 12-megapixel photo (`4000 x 3000` JPEG) before vs. after `1600 px` downscale cap (`backend/app/extraction/extractor.py`):**
  - *Before `1600 px` cap:* `117.76 MB` post-call RSS, **`1,913.51 MB` peak RSS**, `312.79 MB` private commit.
  - *After `1600 px` cap (`4000 x 3000` $\to$ `1600 x 1200`), single-worker `_ocr_lock`, `8 MB` upload cap, and `gc.collect()`:* `115.10 MB` post-call RSS, **`450.19 MB` peak RSS**, `309.89 MB` private commit.

> **512 MB Free-Tier Risk Flag:** Downscaling a 12-MP photo to `1600 px` cut peak RSS by **4.25x** (`1,913.51 MB` $\to$ `450.19 MB`), preventing catastrophic multi-GB OOM spikes, **but `450.19 MB` peak RSS still exceeds a `350 MB` safety target and approaches Render's `512 MB` hard ceiling** when FastAPI/Uvicorn and RapidOCR ONNX sessions run together. Keep `uvicorn` at 1 worker behind `_ocr_lock` on free tier, or upgrade to a 1 GB+ instance for production mobile photo OCR. Note also that Render free-tier instances spin down after inactivity (~1 min cold start); the frontend [`BackendStatusChip`](../frontend/src/components/BackendStatusChip.tsx) and upload UI surface a retry state for cold starts.

*(Docker image build size was not measured locally because `docker` CLI/daemon is unavailable on this host.)*

---

## 4. Incognito & Mobile Phone Pre-Launch Test Checklist

Run this checklist in both a **Desktop Incognito window** and a **mobile browser (iOS Safari / Android Chrome)** against the live Vercel + Render URLs:

1. **Backend Health & Cold Start:**
   - Open the Vercel URL.
   - Verify the top-right status chip transitions from `Checking backend...` (or `Backend unreachable, retry (cold start may take ~1 min)` during Render wake-up) to `Backend ready`.
   - Click `Retry` if Render is waking up and confirm it recovers cleanly without page reload.
2. **CORS Enforcement:**
   - Open DevTools Console / Network tab and verify zero CORS errors on `/api/health`, `/api/sample-reports`, and `/api/extract`.
3. **Local-Only Default Flow (`Cloud AI` toggle OFF):**
   - Click **Load Selected Sample Report** on `02_metropolis_prediabetic.pdf` and verify extraction completes locally (`model_used` shows `heuristic-rule-engine (local-only)`) with **zero** OpenRouter calls and **no** preview dialog.
   - Confirm values in the confirmation table -> verify **Levine PhenoAge**, **Risk Flags**, **Clinician PDF** download, and **HL7 FHIR JSON** download work on both desktop and mobile.
4. **Opt-In Cloud Preview Flow (`Cloud AI` toggle ON):**
   - Enable `Cloud AI Consent (OpenRouter)`.
   - Upload a real/test report or select a sample report and verify the **"What Will Be Sent to OpenRouter"** preview appears **before** any cloud request fires.
   - Confirm personal details (name, phone, email, IDs, dates, addresses) are redacted and `Exact payload notice` is visible.
   - Test **Cancel (Use Local Extraction)** -> verify local extraction runs cleanly with no OpenRouter call.
   - Re-test with **Send** -> confirm cloud extraction completes.
5. **AI Companion Consent & Privacy Guardrails:**
   - With consent OFF, open AI Companion -> verify it prompts to enable consent and cannot chat.
   - Enable consent and send a message containing a self-intro name/phone (or routine biomarker question) -> confirm reply renders cleanly on mobile viewport without horizontal overflow.
