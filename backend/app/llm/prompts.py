# backend/app/llm/prompts.py
import json

SYSTEM_PROMPT = """You are an expert clinical laboratory data extraction system.
Your job is to accurately extract structured biomarker data from raw medical lab reports (text or OCR output).

RULES:
1. Strict Fidelity: Extract ONLY what is explicitly present in the report. NEVER guess, interpolate, or invent missing values.
2. Canonical Mapping: Map laboratory test names to the canonical standard_id from the approved list whenever applicable.
3. Unit Preservation: Capture both the original unit and standard unit.
4. Confidence & Review: Assign a realistic confidence score (0.0 to 1.0). If text is blurry, truncated, or ambiguous, assign < 0.8 and mark needs_review: true.
5. Reference Ranges: Parse numeric low and high limits when provided. If none or complex, record in reference_range.text.
6. Flags: Mark flag as "low" (below low range), "high" (above high range), "normal" (within range), or "unknown".
7. Format: Return ONLY raw, valid JSON matching the specified schema. No markdown formatting, no conversational prose.
"""

EXTRACTION_SCHEMA_INSTRUCTION = """
Approved standard_id values:
- Core PhenoAge: "albumin", "creatinine", "glucose_fasting", "crp", "lymphocyte_pct", "mcv", "rdw", "alp", "wbc"
- Routine/Metabolic: "hemoglobin", "platelets", "hba1c", "cholesterol_total", "cholesterol_hdl", "cholesterol_ldl", "triglycerides", "vldl", "bilirubin_total", "ast_sgot", "alt_sgpt", "bun", "uric_acid", "egfr", "sodium", "potassium", "other"

JSON Output Structure:
{
  "patient_info": {
    "name": "string or null",
    "age": number or null,
    "gender": "male | female | other | null",
    "report_date": "YYYY-MM-DD or null",
    "lab_name": "string or null"
  },
  "biomarkers": [
    {
      "standard_id": "canonical_id",
      "display_name": "Standard Human Name",
      "raw_name": "Name as seen in report",
      "value": number or null,
      "unit": "string",
      "standard_unit": "string",
      "reference_range": {
        "low": number or null,
        "high": number or null,
        "text": "string or null"
      },
      "confidence": number between 0.0 and 1.0,
      "flag": "low | normal | high | critical | unknown",
      "needs_review": boolean,
      "source_text": "Exact text line where this was found"
    }
  ]
}
"""


def build_extraction_prompt(raw_text: str) -> str:
    return f"""{EXTRACTION_SCHEMA_INSTRUCTION}

RAW LAB REPORT TEXT TO PARSE:
-----------------------------
{raw_text}
-----------------------------

Output the extracted JSON now:"""


def build_retry_prompt(raw_text: str, error_message: str) -> str:
    return f"""Your previous output failed validation with the following error:
{error_message}

Please re-parse the raw report text and return ONLY valid, well-formed JSON matching the required schema.

RAW LAB REPORT TEXT:
-----------------------------
{raw_text}
-----------------------------

Corrected JSON Output:"""
