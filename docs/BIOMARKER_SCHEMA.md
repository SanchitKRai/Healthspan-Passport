# Healthspan Passport - Biomarker JSON Schema Specification (Contract v1.0)

> **Status:** Agreed & Frozen (Contract between Frontend and Backend)
> **Date:** 2026-11-21
> **Rule:** This is the shared contract. Neither Backend nor Frontend should modify these field names or schemas without explicit agreement.

---

## 1. Top-Level Extraction Response

```json
{
  "patient_info": {
    "name": "string | null",
    "age": "number | null",
    "gender": "male | female | other | null",
    "report_date": "string (YYYY-MM-DD) | null",
    "lab_name": "string | null"
  },
  "biomarkers": [
    {
      "standard_id": "string (CanonicalBiomarker enum)",
      "display_name": "string",
      "raw_name": "string",
      "value": "number | null",
      "unit": "string",
      "standard_unit": "string",
      "reference_range": {
        "low": "number | null",
        "high": "number | null",
        "text": "string | null"
      },
      "confidence": "number (0.0 to 1.0)",
      "flag": "low | normal | high | critical | unknown",
      "needs_review": "boolean",
      "source_text": "string | null",
      "bounding_box": {
        "page": "number",
        "x0": "number",
        "y0": "number",
        "x1": "number",
        "y1": "number"
      }
    }
  ],
  "extraction_metadata": {
    "model_used": "string",
    "extraction_duration_ms": "number",
    "raw_text_length": "number",
    "total_biomarkers_found": "number",
    "low_confidence_count": "number",
    "missing_phenoage_biomarkers": ["string"]
  }
}
```

---

## 2. Canonical Biomarker IDs (`standard_id`)

### Core PhenoAge Biomarkers (9 Blood Markers + Age)
1. `albumin`: Serum Albumin (standard unit: `g/dL`)
2. `creatinine`: Serum Creatinine (standard unit: `mg/dL`)
3. `glucose_fasting`: Fasting Blood Glucose (standard unit: `mg/dL`)
4. `crp`: C-Reactive Protein / hs-CRP (standard unit: `mg/L`)
5. `lymphocyte_pct`: Lymphocyte Percentage (standard unit: `%`)
6. `mcv`: Mean Corpuscular Volume (standard unit: `fL`)
7. `rdw`: Red Cell Distribution Width (standard unit: `%`)
8. `alp`: Alkaline Phosphatase (standard unit: `U/L`)
9. `wbc`: White Blood Cell Count / TLC (standard unit: `10^3/uL` or `10^9/L`)

### Additional Routine Preventive & Metabolic Biomarkers
10. `hemoglobin`: Hemoglobin / Hb (`g/dL`)
11. `platelets`: Platelet Count (`10^3/uL`)
12. `hba1c`: Glycated Hemoglobin (`%`)
13. `cholesterol_total`: Total Cholesterol (`mg/dL`)
14. `cholesterol_hdl`: High-Density Lipoprotein (`mg/dL`)
15. `cholesterol_ldl`: Low-Density Lipoprotein (`mg/dL`)
16. `triglycerides`: Triglycerides (`mg/dL`)
17. `vldl`: Very Low-Density Lipoprotein (`mg/dL`)
18. `bilirubin_total`: Total Bilirubin (`mg/dL`)
19. `ast_sgot`: Aspartate Aminotransferase (`U/L`)
20. `alt_sgpt`: Alanine Aminotransferase (`U/L`)
21. `bun`: Blood Urea Nitrogen / Urea (`mg/dL`)
22. `uric_acid`: Uric Acid (`mg/dL`)
23. `egfr`: Estimated Glomerular Filtration Rate (`mL/min/1.73m2`)
24. `sodium`: Serum Sodium (`mEq/L` or `mmol/L`)
25. `potassium`: Serum Potassium (`mEq/L` or `mmol/L`)

---

## 3. Flagging & Review Rules

- **`confidence`**: Estimated confidence between `0.0` and `1.0`. Any value with confidence `< 0.8` sets `needs_review: true`.
- **`needs_review`**: True if:
  1. `confidence < 0.8`
  2. `value === null` for a detected marker
  3. Extracted value is outside biologically plausible physiological limits (e.g., Albumin > 15 g/dL or Glucose < 10 mg/dL).
- **`flag`**:
  - `normal`: Within reference range `[low, high]`
  - `low`: Below `low`
  - `high`: Above `high`
  - `critical`: Extreme outliers based on clinical thresholds
  - `unknown`: No reference range available or value is null

---

## 4. Endpoints Implementing This Contract

- `POST /api/extract`: Uploads multipart file (`file: UploadFile`), returns the top-level extraction response JSON.
- `GET /api/sample-reports`: Returns list of available sample reports (`[{ id, filename, label, format }]`).
- `POST /api/extract-sample/{filename}`: Runs extraction on one of the built-in sample reports.
