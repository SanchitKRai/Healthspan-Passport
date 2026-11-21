# Day 3 & Day 4: Validation Proof & Interactive Differentiators Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement extraction benchmark against ground truth, reproducible NHANES PhenoAge validation pipeline with mortality correlation, What-If biological age slider simulator, multi-report longitudinal trend tracker with local storage & privacy controls, and bilingual (English/Hindi) plain-language explainer with Web Speech voice synthesis.

**Architecture:**
- Backend validation modules:
  - `benchmark_extraction.py` processes all 15 sample reports against `ground_truth.json`, measuring field accuracy (split by PDF vs phone capture), low-confidence flag rate, and safety-critical unflagged error rate.
  - `validate_nhanes.py` tests Levine PhenoAge against NHANES cohort data, calculating Pearson correlation ($r$) with age and mortality hazard across quartiles, plotting `nhanes_validation.png`, and recording findings in `VALIDATION_RESULTS.md`.
  - `POST /api/explain` generates structured bilingual explanations (English and Hindi), vegetarian-friendly diet tips, and physician questions grounded strictly in biomarker data.
- Frontend components:
  - `WhatIfSimulator.tsx`: Real-time reactive sliders for modifiable markers (Glucose, hs-CRP, Albumin, Lymphocyte %, WBC, RDW) with instant PhenoAge delta.
  - `TrendsView.tsx`: Multi-report timeline charts using Recharts with 1-click 3-year historical demo loader and privacy wipe.
  - `BilingualExplainer.tsx`: English/Hindi toggle with Web Speech API audio playback.

**Tech Stack:** Python 3.14, FastAPI, Pandas, Matplotlib, Scipy, Next.js 15, Recharts, Tailwind CSS, TypeScript.

---

### Task 1: Module 1 - Extraction Accuracy Benchmark (`backend/scripts/benchmark_extraction.py`)

**Files:**
- Create: `backend/scripts/benchmark_extraction.py`
- Create: `data/benchmark_metrics.json`
- Create: `docs/VALIDATION_RESULTS.md`
- Test: `backend/tests/test_benchmark.py`

**Interfaces:**
- Produces: `run_benchmark() -> Dict[str, Any]` outputting:
  - Overall field accuracy (%)
  - Digital PDF accuracy (%) vs. Phone photo accuracy (%)
  - Rate of low confidence / needs review flags
  - Safety-critical unflagged error rate

- [ ] **Step 1: Write test for benchmark metrics calculation logic**
- [ ] **Step 2: Run pytest to verify test fails (RED)**
- [ ] **Step 3: Implement `backend/scripts/benchmark_extraction.py` and run benchmark**
- [ ] **Step 4: Verify `data/benchmark_metrics.json` and `docs/VALIDATION_RESULTS.md` are populated and tests pass (GREEN)**
- [ ] **Step 5: Commit**

---

### Task 2: Module 2 - NHANES PhenoAge Mortality Validation Script (`backend/scripts/validate_nhanes.py`)

**Files:**
- Create: `backend/scripts/validate_nhanes.py`
- Create: `docs/nhanes_validation.png`
- Modify: `docs/VALIDATION_RESULTS.md`
- Test: `backend/tests/test_nhanes_validation.py`

**Interfaces:**
- Produces: Reproducible statistical pipeline computing:
  - Cohort $N$ and cycle details
  - Pearson correlation $r$ between computed PhenoAge and chronological age
  - 10-year mortality association across PhenoAge acceleration quartiles
  - Saves high-resolution chart `docs/nhanes_validation.png` and updates `docs/VALIDATION_RESULTS.md`.

- [ ] **Step 1: Write unit tests verifying NHANES scoring, correlation, and quartile statistics functions**
- [ ] **Step 2: Run pytest to verify test fails (RED)**
- [ ] **Step 3: Implement `backend/scripts/validate_nhanes.py` and execute validation run**
- [ ] **Step 4: Verify output plot `docs/nhanes_validation.png` generated and test passes (GREEN)**
- [ ] **Step 5: Commit**

---

### Task 3: Module 3 - What-If Biological Age Simulator & Trend Engine (`/frontend`)

**Files:**
- Modify: `frontend/package.json` (add `recharts`)
- Create: `frontend/src/components/WhatIfSimulator.tsx`
- Create: `frontend/src/components/TrendsView.tsx`
- Create: `frontend/src/data/demoTrends.ts` (3-year historical reports dataset: 2024, 2025, 2026)
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- What-If Simulator: Reactive sliders for modifiable markers with instant delta display.
- TrendsView: Line charts for PhenoAge, Fasting Glucose, hs-CRP, and Cholesterol across time with local storage persistence and one-click data purge.

- [ ] **Step 1: Install `recharts` in `frontend/`**
- [ ] **Step 2: Implement `demoTrends.ts` with 3-year historical longitudinal data**
- [ ] **Step 3: Implement `WhatIfSimulator.tsx` with modifiable sliders and real-time Levine 2018 recalculation**
- [ ] **Step 4: Implement `TrendsView.tsx` with Recharts charts and localStorage management**
- [ ] **Step 5: Integrate into `frontend/src/app/page.tsx` and verify `npm run build`**
- [ ] **Step 6: Commit**

---

### Task 4: Module 4 - Plain-Language Bilingual Explainer (English & Hindi) + Voice Output

**Files:**
- Create: `backend/app/core/explainer.py`
- Modify: `backend/app/schemas/biomarker.py` (Add `ExplanationResponse`, `ExplanationRequest`)
- Modify: `backend/app/main.py` (Add `POST /api/explain`)
- Create: `backend/tests/test_explainer.py`
- Create: `frontend/src/components/BilingualExplainer.tsx`
- Modify: `frontend/src/app/page.tsx`

**Interfaces:**
- `POST /api/explain`: Returns English & Hindi plain-language sections, Indian vegetarian dietary guidance, and doctor discussion points.
- Frontend: English/हिंदी tab toggle with Web Speech API audio playback (`window.speechSynthesis`).

- [ ] **Step 1: Write failing tests for bilingual explanation generation and doctor questions in `test_explainer.py`**
- [ ] **Step 2: Run pytest to verify test fails (RED)**
- [ ] **Step 3: Implement `explainer.py` and `POST /api/explain` endpoint in FastAPI**
- [ ] **Step 4: Run pytest to verify test passes (GREEN)**
- [ ] **Step 5: Implement `BilingualExplainer.tsx` in Next.js with Web Speech API**
- [ ] **Step 6: Verify `npm run build` passes cleanly**
- [ ] **Step 7: Commit**

---

### Task 5: End-to-End Verification & GitHub Push

- [ ] **Step 1: Run full pytest suite (all 26+ tests)**
- [ ] **Step 2: Verify `POST /api/explain` live**
- [ ] **Step 3: Verify What-If simulator and Trends Recharts in frontend**
- [ ] **Step 4: Push all commits to GitHub remote**
