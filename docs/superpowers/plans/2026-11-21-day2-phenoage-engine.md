# Day 2: Unit Normalization, PhenoAge Engine, Risk Flags & Confirmation UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement unit normalization, the published Levine (2018) PhenoAge biological age model, non-diagnostic multi-organ risk flags, analysis API endpoint, and a human-in-the-loop confirmation & analysis dashboard in Next.js.

**Architecture:** A robust unit normalizer converts raw biomarker measurements to canonical units and maps Indian reference ranges. A pure Python PhenoAge engine calculates biological age from 9 core blood markers + chronological age (or returns null with exact missing markers if CRP/others are missing). A non-diagnostic risk engine categorizes metabolic, cardiovascular, renal, hepatic, and hematologic risk. A new `POST /api/analyze` endpoint processes confirmed user values, while the Next.js frontend enables inline value confirmation before displaying biological age and risk cards.

**Tech Stack:** Python 3.14, FastAPI, Pydantic v2, pytest, Next.js 15, Tailwind CSS, TypeScript.

**Spec:** User prompt requirements, Levine et al. (2018) PhenoAge specification, `docs/BIOMARKER_SCHEMA.md`.

## Global Constraints

- Backend directory: `/backend`
- Frontend directory: `/frontend`
- Biological Age Formula: Levine et al. (2018) PhenoAge formula with exact published coefficients.
- Strict missing-input rule: If any of the 9 PhenoAge markers are missing, biological age MUST be `null` and list missing tests. NEVER impute.
- Risk flags: Educational and preventive wording ONLY. Never say "you have a disease" or provide a diagnosis.
- Population limitation note: Must explicitly state PhenoAge was trained on US population data; results for Indian users are estimates.
- Negative constraints: DO NOT add Hindi yet (Day 4), DO NOT add Trends/What-If sliders yet (Day 3), keep UI clean/minimal Tailwind (white background, no decorative flair).

## Review Focus

1. Unit conversion edge cases (e.g. converting WBC `cells/cumm` vs `10^3/µL`, CRP `mg/L` vs `mg/dL`, Glucose `mg/dL` vs `mmol/L`).
2. Logarithm of CRP when CRP is 0 or extremely low (must use numerical floor to avoid `log(0)` crash).
3. Missing CRP handling: verify risk flags still calculate and display normally even when PhenoAge is null.
4. Human-in-the-loop confirmation: verify editing a low-confidence value in the frontend updates the analysis payload sent to `/api/analyze`.
5. Edge cases in age/biomarkers: ensure extreme values don't crash with math domain errors in PhenoAge calculation.

---

### Task 1: Unit Normalizer & Indian Reference Ranges (`backend/app/core/normalizer.py`)

**Files:**
- Create: `backend/app/core/__init__.py`
- Create: `backend/app/core/normalizer.py`
- Create: `backend/tests/test_normalizer.py`

**Interfaces:**
- Produces: `normalize_biomarker(standard_id: str, value: float, unit: str) -> Tuple[float, str, ReferenceRange]` converting:
  - Albumin: `g/dL` -> `g/L` ($\times 10$)
  - Creatinine: `mg/dL` -> `µmol/L` ($\times 88.4$)
  - Glucose: `mg/dL` -> `mmol/L` ($\div 18.0182$)
  - CRP: `mg/L` -> `mg/dL` ($\div 10$)
  - WBC: `cells/cumm` or `/µL` -> `10^9/L` ($\div 1000$)
  - Plus Indian reference ranges for HbA1c, Fasting Glucose, Lipids, Hemoglobin (by sex), Uric Acid, etc.

- [ ] **Step 1: Write failing tests for unit normalizer conversions and Indian reference ranges**
- [ ] **Step 2: Run pytest to verify tests fail (RED)**
- [ ] **Step 3: Implement `backend/app/core/normalizer.py`**
- [ ] **Step 4: Run pytest to verify tests pass (GREEN)**
- [ ] **Step 5: Commit**

---

### Task 2: Levine (2018) PhenoAge & Risk Flag Engine (`backend/app/core/phenoage.py`)

**Files:**
- Create: `backend/app/core/phenoage.py`
- Create: `backend/tests/test_phenoage.py`

**Interfaces:**
- Produces:
  - `calculate_phenoage(biomarkers: Dict[str, float], chronological_age: float) -> PhenoAgeResult`
  - `evaluate_risk_flags(biomarkers: Dict[str, float], sex: Optional[str] = None) -> List[RiskFlagCategory]`
  - Where `PhenoAgeResult` contains `phenoage: Optional[float]`, `age_acceleration: Optional[float]`, `is_valid: bool`, `missing_markers: List[str]`, `mortality_score_10yr: Optional[float]`.

- [ ] **Step 1: Write failing tests for exact PhenoAge calculations (verified against reference values) and missing-input handling**
- [ ] **Step 2: Run pytest to verify tests fail (RED)**
- [ ] **Step 3: Implement `calculate_phenoage` and `evaluate_risk_flags` in `backend/app/core/phenoage.py`**
- [ ] **Step 4: Run pytest to verify tests pass (GREEN)**
- [ ] **Step 5: Commit**

---

### Task 3: Analysis API Endpoint & Schema Integration (`POST /api/analyze`)

**Files:**
- Modify: `backend/app/schemas/biomarker.py` (Add `AnalysisRequest`, `AnalysisResponse`, `RiskFlagItem`, `RiskFlagCategory`)
- Modify: `backend/app/main.py` (Implement `POST /api/analyze`)
- Create: `backend/tests/test_analyze_api.py`

**Interfaces:**
- Consumes: `AnalysisRequest(patient_age: float, patient_gender: Optional[str], biomarkers: List[BiomarkerItem])`
- Produces: `AnalysisResponse` containing normalized biomarkers, `phenoage_result`, `risk_flags`, and `population_caveat`.

- [ ] **Step 1: Write failing tests for `POST /api/analyze` (both full 9-marker report and missing-CRP report)**
- [ ] **Step 2: Run pytest to verify tests fail (RED)**
- [ ] **Step 3: Implement `AnalysisRequest`/`AnalysisResponse` schemas and `/api/analyze` endpoint in `backend/app/main.py`**
- [ ] **Step 4: Run pytest to verify tests pass (GREEN)**
- [ ] **Step 5: Commit**

---

### Task 4: Frontend Human-in-the-Loop Confirmation & Analysis Dashboard

**Files:**
- Modify: `frontend/src/types/biomarker.ts` (Add `AnalysisRequest`, `AnalysisResponse`, `RiskFlagCategory`)
- Create: `frontend/src/components/ConfirmationTable.tsx` (Editable values, units, age input, and confirm button)
- Create: `frontend/src/components/PhenoAgeCard.tsx` (Biological age vs Chronological age, acceleration, missing CRP alert, population caveat)
- Create: `frontend/src/components/RiskFlagsSection.tsx` (Categorized cards for glycemic, lipid, renal, hepatic, hematologic)
- Modify: `frontend/src/app/page.tsx` (Wire confirmation flow into analysis dashboard)

**Interfaces:**
- Consumes: `POST http://localhost:8000/api/analyze`
- Produces: Interactive workflow: Upload -> Extracted values table (editable with needs_review highlights) -> "Confirm & Calculate" -> Biological Age & Risk Flag cards.

- [ ] **Step 1: Update TypeScript types in `frontend/src/types/biomarker.ts`**
- [ ] **Step 2: Implement `ConfirmationTable.tsx` allowing user value edits and chronological age entry**
- [ ] **Step 3: Implement `PhenoAgeCard.tsx` and `RiskFlagsSection.tsx`**
- [ ] **Step 4: Update `frontend/src/app/page.tsx` to handle confirmation and display analysis**
- [ ] **Step 5: Verify build compiles cleanly with `npm run build`**
- [ ] **Step 6: Commit**

---

### Task 5: End-to-End Verification of Day 2

- [ ] **Step 1: Run full pytest suite (all normalizer, phenoage, and analyze tests)**
- [ ] **Step 2: Test `POST /api/analyze` with `01_dr_lal_healthy_adult.pdf` (all 9 markers present -> valid PhenoAge)**
- [ ] **Step 3: Test `POST /api/analyze` with `06_quest_missing_crp.pdf` (CRP missing -> PhenoAge null with clear alert, risk flags computed)**
- [ ] **Step 4: Verify Next.js frontend end-to-end**
