# MVP Extraction Pipeline Implementation Plan

> **INTEGRITY AUDIT NOTICE (2026-11-27):** Historical plan preserved for reference. On branch `day1-integrity`, note that `backend/app/llm/client.py` uses `nvidia/nemotron-3.5-lightning` and `moonshotai/kimi-k2`, the 15 reports in `data/sample_reports/` are synthetic, and the offline simulated bake-off report (`docs/BAKEOFF_RESULTS.md`) was removed.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and verify an end-to-end report extraction pipeline with a FastAPI backend, OpenRouter LLM extraction (Nemotron/Kimi), and a Next.js frontend showing extracted biomarkers in a table from 15 diverse lab reports.

**Architecture:** A modular FastAPI service parses lab reports (PDF via `pdfplumber`, images via `RapidOCR`/fallback), invokes an OpenRouter LLM client with strict JSON schema validation and 1 retry, and standardizes outputs to a frozen biomarker contract. A lightweight Next.js frontend provides file upload and sample selection, rendering extracted biomarkers with confidence ratings and review flags.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pdfplumber, RapidOCR / PIL, httpx (OpenRouter API), Next.js 15/React 19, Tailwind CSS.

**Spec:** [docs/BIOMARKER_SCHEMA.md](file:///C:/Users/lenovo/.gemini/antigravity/scratch/Healthspan-Passport/docs/BIOMARKER_SCHEMA.md) and User Request.

## Global Constraints

- Backend directory: `/backend`
- Frontend directory: `/frontend`
- Contract: strictly follow [docs/BIOMARKER_SCHEMA.md](file:///C:/Users/lenovo/.gemini/antigravity/scratch/Healthspan-Passport/docs/BIOMARKER_SCHEMA.md)
- Primary Model: Nemotron (`nvidia/llama-3.1-nemotron-70b-instruct`)
- Fallback Model: Kimi (`moonshotai/moonshot-v1-auto` or verified Kimi model slug from OpenRouter `/api/v1/models`, e.g. `moonshotai/kimi-k2`)
- Ground Truth: In Task 5, save corresponding `data/ground_truth.json` mapping each filename to exact ground-truth biomarker values and units.
- Robust fallback/mocking: If `OPENROUTER_API_KEY` is not provided in environment, fallback to structured heuristic/rule-based extractor so full end-to-end flow and test suite run without failing.
- Constraints from user: DO NOT style anything (minimal/clean Tailwind only), DO NOT add Hindi, DO NOT touch PhenoAge.

## Review Focus

1. Text extraction failure on multi-page or scanned PDFs: graceful handling without crashing.
2. Malformed JSON from LLM: verify 1 automatic retry triggers with corrective prompt.
3. Missing essential biomarkers: correctly identify missing PhenoAge input list in metadata without guessing values.
4. Out-of-bounds or invalid units: mark `needs_review: true` for abnormal or low-confidence values.
5. Large image / skewed image OCR: ensure OCR does not hang and extracts readable lines.

---

### Task 1: Repository Structure & Contract Implementation

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/schemas/biomarker.py`
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/test_schemas.py`
- Create: `frontend/src/types/biomarker.ts`

**Interfaces:**
- Consumes: `docs/BIOMARKER_SCHEMA.md`
- Produces: `BiomarkerItem`, `PatientInfo`, `ExtractionResponse`, `ExtractionMetadata` Pydantic models and TypeScript interfaces.

- [ ] **Step 1: Write failing test for Pydantic biomarker schemas**
- [ ] **Step 2: Run pytest to verify test fails**
- [ ] **Step 3: Implement Pydantic schema in `backend/app/schemas/biomarker.py` and TypeScript definitions in `frontend/src/types/biomarker.ts`**
- [ ] **Step 4: Run pytest to verify test passes**
- [ ] **Step 5: Commit**

---

### Task 2: Multi-Format Text Extraction Layer (`pdfplumber` & `RapidOCR`)

**Files:**
- Create: `backend/app/extraction/__init__.py`
- Create: `backend/app/extraction/extractor.py`
- Create: `backend/tests/test_extraction.py`

**Interfaces:**
- Consumes: Raw bytes / file path of PDF or image.
- Produces: `extract_text_from_file(file_bytes: bytes, filename: str) -> Tuple[str, dict]` returning extracted raw text and extraction metadata.

- [ ] **Step 1: Write failing test for PDF and image text extractor**
- [ ] **Step 2: Run pytest to verify test fails**
- [ ] **Step 3: Implement `extractor.py` using `pdfplumber` for PDFs and `RapidOCR`/PIL fallback for images**
- [ ] **Step 4: Run pytest to verify test passes**
- [ ] **Step 5: Commit**

---

### Task 3: OpenRouter Client with Primary/Fallback & Retry Validation

**Files:**
- Create: `backend/app/llm/__init__.py`
- Create: `backend/app/llm/client.py`
- Create: `backend/app/llm/prompts.py`
- Create: `backend/tests/test_llm.py`

**Interfaces:**
- Consumes: Extracted raw text.
- Produces: `extract_biomarkers_with_llm(raw_text: str) -> ExtractionResponse` using Nemotron with fallback to Kimi and 1 retry on malformed JSON; includes local heuristic fallback when API key is unset.

- [ ] **Step 1: Write failing test for LLM client and retry logic**
- [ ] **Step 2: Run pytest to verify test fails**
- [ ] **Step 3: Implement prompt template and OpenRouter client with dual models, retry validation, and mock fallback**
- [ ] **Step 4: Run pytest to verify test passes**
- [ ] **Step 5: Commit**

---

### Task 4: FastAPI Application & Endpoints

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/tests/test_api.py`
- Create: `backend/requirements.txt`

**Interfaces:**
- Consumes: `extractor.py` and `client.py`
- Produces:
  - `POST /api/extract`
  - `GET /api/sample-reports`
  - `POST /api/extract-sample/{filename}`
  - `GET /api/health`

- [ ] **Step 1: Write failing API endpoint tests with `TestClient`**
- [ ] **Step 2: Run pytest to verify test fails**
- [ ] **Step 3: Implement FastAPI app with CORS and file upload handling**
- [ ] **Step 4: Run pytest to verify test passes**
- [ ] **Step 5: Commit**

---

### Task 5: 15 Sample Reports & Model Bake-off Script

**Files:**
- Create: `data/sample_reports/` (15 report files: 8 PDFs, 7 images)
- Create: `data/ground_truth.json` (Ground truth mapping for all 15 reports for Day 4 benchmark)
- Create: `backend/scripts/generate_sample_reports.py`
- Create: `backend/scripts/bakeoff.py`

**Interfaces:**
- Produces: 15 diverse sample lab reports (standard routine panels, skewed/noisy image captures, borderline/anemic/diabetic profiles, missing-CRP profile), `data/ground_truth.json` with ground-truth values/units, and bake-off benchmark between Nemotron and Kimi.

- [ ] **Step 1: Implement report generator script to produce 15 diverse lab report files and `data/ground_truth.json`**
- [ ] **Step 2: Run generator script to create files in `data/sample_reports/` and `data/ground_truth.json`**
- [ ] **Step 3: Implement `backend/scripts/bakeoff.py` comparing Nemotron vs Kimi on 5 representative reports**
- [ ] **Step 4: Commit**

---

### Task 6: Next.js Frontend (Upload Page & Results Table)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/UploadSection.tsx`
- Create: `frontend/src/components/BiomarkerTable.tsx`
- Create: `frontend/src/components/PatientSummary.tsx`

**Interfaces:**
- Consumes: `POST http://localhost:8000/api/extract`, `GET http://localhost:8000/api/sample-reports`
- Produces: Clean, unstyled/minimal Next.js app with file drag-and-drop, sample report dropdown, and structured table displaying all extracted biomarkers, confidence scores, and review warnings.

- [ ] **Step 1: Scaffold Next.js frontend with Tailwind and TypeScript**
- [ ] **Step 2: Implement Upload component with file input and sample report selector**
- [ ] **Step 3: Implement Results Table displaying extracted biomarkers, units, flags, confidence, and review alerts**
- [ ] **Step 4: Verify frontend build compiles successfully with `npm run build`**
- [ ] **Step 5: Commit**

---

### Task 7: End-to-End Verification (Exit Check)

- [ ] **Step 1: Start backend server on port 8000**
- [ ] **Step 2: Start frontend dev server on port 3000**
- [ ] **Step 3: Upload a sample report and verify correct extracted values render on screen**
- [ ] **Step 4: Final verification and summary**
