import os
import re
import time
import json
import logging
from typing import Optional, Dict, Any, Tuple
import httpx

from app.schemas.biomarker import (
    ExtractionResponse,
    PatientInfo,
    BiomarkerItem,
    ExtractionMetadata,
    CanonicalBiomarker,
    BiomarkerFlag,
    ReferenceRange,
    PHENOAGE_CORE_BIOMARKERS,
    PHYSIOLOGICAL_LIMITS,
)
from app.core.normalizer import BIOMARKER_ALIASES
from app.llm.prompts import SYSTEM_PROMPT, build_extraction_prompt, build_retry_prompt
from app.llm.redact import _NON_RESULT_CONTEXT_LINE, _STANDALONE_UNIT_REGEX, minimize_to_result_lines, redact_pii

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Single primary OpenRouter model selected from live N=3 evaluation (falls back to local heuristic).
PRIMARY_MODEL = os.getenv("OPENROUTER_PRIMARY_MODEL", "mistralai/mistral-small-3.2-24b-instruct")
FALLBACK_MODEL: Optional[str] = os.getenv("OPENROUTER_FALLBACK_MODEL") or None


def clean_json_string(text: str) -> str:
    """Extract and clean JSON payload from LLM response text."""
    text = text.strip()
    
    # 1. Check for markdown code fence pattern
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence_match:
        return fence_match.group(1).strip()
    
    # 2. Extract substring between outermost braces { ... }
    first_brace = text.find("{")
    last_brace = text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return text[first_brace : last_brace + 1].strip()
        
    return text


def safe_to_float(val: Any) -> Optional[float]:
    """Safely convert arbitrary values or strings like '<0.5' / '45 yrs' to float."""
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return float(val)
    try:
        cleaned = re.sub(r"[<>=]", "", str(val)).strip()
        num_match = re.search(r"[-+]?[0-9]*\.?[0-9]+", cleaned)
        if num_match:
            return float(num_match.group(0))
        return None
    except (ValueError, TypeError):
        return None


def parse_and_validate_extraction(
    json_str: str,
    raw_text: str,
    model_name: str,
    duration_ms: int
) -> ExtractionResponse:
    """Parse JSON string and construct a valid ExtractionResponse."""
    cleaned = clean_json_string(json_str)
    data = json.loads(cleaned)

    patient_raw = data.get("patient_info") or {}
    patient_info = PatientInfo(
        name=patient_raw.get("name"),
        age=safe_to_float(patient_raw.get("age")),
        gender=patient_raw.get("gender"),
        report_date=patient_raw.get("report_date"),
        lab_name=patient_raw.get("lab_name"),
    )

    biomarkers = []
    low_confidence_count = 0
    extracted_canonical_ids = set()

    raw_biomarkers = data.get("biomarkers") or []
    for item in raw_biomarkers:
        try:
            standard_id_str = str(item.get("standard_id", "")).lower().strip()
            # Map or fallback to OTHER if not in CanonicalBiomarker
            try:
                standard_id = CanonicalBiomarker(standard_id_str)
            except ValueError:
                standard_id = CanonicalBiomarker.OTHER

            ref_raw = item.get("reference_range") or {}
            ref_range = ReferenceRange(
                low=safe_to_float(ref_raw.get("low")),
                high=safe_to_float(ref_raw.get("high")),
                text=ref_raw.get("text"),
            )

            confidence = safe_to_float(item.get("confidence"))
            if confidence is None:
                confidence = 0.9

            flag_str = str(item.get("flag", "normal")).lower()
            try:
                flag = BiomarkerFlag(flag_str)
            except ValueError:
                flag = BiomarkerFlag.NORMAL

            value = safe_to_float(item.get("value"))

            bio_item = BiomarkerItem(
                standard_id=standard_id,
                display_name=item.get("display_name", standard_id.value.replace("_", " ").title()),
                raw_name=item.get("raw_name", standard_id.value),
                value=value,
                unit=item.get("unit", ""),
                standard_unit=item.get("standard_unit", item.get("unit", "")),
                reference_range=ref_range,
                confidence=confidence,
                flag=flag,
                needs_review=bool(item.get("needs_review", False) or confidence < 0.8 or value is None),
                source_text=item.get("source_text"),
            )
            biomarkers.append(bio_item)
            if bio_item.needs_review:
                low_confidence_count += 1
            if standard_id != CanonicalBiomarker.OTHER:
                extracted_canonical_ids.add(standard_id.value)
        except Exception as e:
            std_label = item.get("standard_id", "unknown") if isinstance(item, dict) else "unknown"
            logger.warning("Skipping malformed biomarker item (%s): %s", std_label, type(e).__name__)

    missing_phenoage = sorted(list(PHENOAGE_CORE_BIOMARKERS - extracted_canonical_ids))

    metadata = ExtractionMetadata(
        model_used=model_name,
        extraction_duration_ms=duration_ms,
        raw_text_length=len(raw_text),
        total_biomarkers_found=len(biomarkers),
        low_confidence_count=low_confidence_count,
        missing_phenoage_biomarkers=missing_phenoage,
    )

    return ExtractionResponse(
        patient_info=patient_info,
        biomarkers=biomarkers,
        extraction_metadata=metadata,
    )


# Comprehensive Heuristic Fallback for local testing / offline runs
# Uses horizontal whitespace [^\S\r\n]* to prevent cross-line bleeding on tabular OCR outputs
HEURISTIC_PATTERNS = [
    # standard_id, display_name, regex, unit, std_unit, (low, high)
    ("albumin", "Serum Albumin", r"(?:serum[^\S\r\n]+)?albumin[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(g/dl|g/l)?", "g/dL", "g/dL", (3.5, 5.2)),
    ("creatinine", "Serum Creatinine", r"(?:serum[^\S\r\n]+)?creatinine[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl|umol/l)?", "mg/dL", "mg/dL", (0.7, 1.3)),
    ("glucose_fasting", "Fasting Blood Glucose", r"(?:fasting[^\S\r\n]+(?:blood[^\S\r\n]+)?(?:sugar|glucose)|glucose[,\s]+fasting)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl|mmol/l)?", "mg/dL", "mg/dL", (70.0, 99.0)),
    ("crp", "C-Reactive Protein", r"(?:hs-?crp|c-reactive protein|crp)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/l|mg/dl)?", "mg/L", "mg/L", (0.0, 3.0)),
    ("lymphocyte_pct", "Lymphocytes Percent", r"(?:lymphocytes?|lymph)[^\S\r\n]*(?:percent|%)?[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(%)?", "%", "%", (20.0, 40.0)),
    ("mcv", "Mean Corpuscular Volume", r"(?:mean[^\S\r\n]+corpuscular[^\S\r\n]+volume(?:[^\S\r\n]*\([^\S\r\n]*mcv[^\S\r\n]*\))?|\bmcv\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(fl)?", "fL", "fL", (80.0, 100.0)),
    ("rdw", "Red Cell Distribution Width", r"(?:red[^\S\r\n]+cell[^\S\r\n]+distribution[^\S\r\n]+width|\brdw(?:-cv)?\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(%)?", "%", "%", (11.5, 14.5)),
    ("alp", "Alkaline Phosphatase", r"(?:alkaline[^\S\r\n]+phosphatase(?:[^\S\r\n]*\([^\S\r\n]*alp[^\S\r\n]*\))?|\balp\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(u/l|iu/l)?", "U/L", "U/L", (44.0, 147.0)),
    ("wbc", "Total Leukocyte Count", r"(?:total[^\S\r\n]+leukocyte[^\S\r\n]+count(?:[^\S\r\n]*\([^\S\r\n]*wbc[^\S\r\n]*\))?|total[^\S\r\n]+wbc(?:[^\S\r\n]+count)?|white[^\S\r\n]+blood[^\S\r\n]+cell[^\S\r\n]+count|\bwbc\b|\btlc\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(?:cells/cumm|10\^3/ul|/ul|x10\^9/l)?", "10^3/uL", "10^3/uL", (4.0, 11.0)),
    ("hemoglobin", "Hemoglobin", r"(?:hemoglobin|\bhb\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(g/dl)?", "g/dL", "g/dL", (12.0, 17.5)),
    ("platelets", "Platelet Count", r"(?:platelet count|\bplatelets\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(?:lakh/cumm|10\^3/ul|/ul)?", "10^3/uL", "10^3/uL", (150.0, 450.0)),
    ("hba1c", "HbA1c", r"\bhba1c\b[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(%)?", "%", "%", (4.0, 5.6)),
    ("cholesterol_total", "Total Cholesterol", r"(?:total[^\S\r\n]+cholesterol|cholesterol[,\s]+total)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (125.0, 200.0)),
    ("cholesterol_hdl", "HDL Cholesterol", r"\bhdl(?:-cholesterol)?[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (40.0, 60.0)),
    ("cholesterol_ldl", "LDL Cholesterol", r"\bldl(?:-cholesterol)?[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (0.0, 100.0)),
    ("triglycerides", "Triglycerides", r"(?:triglycerides|\btg\b)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (0.0, 150.0)),
    ("bilirubin_total", "Total Bilirubin", r"(?:total[^\S\r\n]+bilirubin|bilirubin[,\s]+total)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (0.2, 1.2)),
    ("ast_sgot", "AST / SGOT", r"(?:ast|sgot)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(u/l)?", "U/L", "U/L", (10.0, 40.0)),
    ("alt_sgpt", "ALT / SGPT", r"(?:alt|sgpt)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(u/l)?", "U/L", "U/L", (7.0, 56.0)),
    ("bun", "Blood Urea Nitrogen", r"(?:blood[^\S\r\n]+urea[^\S\r\n]+nitrogen|\bbun\b|urea)[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (7.0, 20.0)),
    ("uric_acid", "Uric Acid", r"uric[^\S\r\n]+acid[^\S\r\n]*[:|]?[^\S\r\n]*([0-9]+(?:\.[0-9]+)?)[^\S\r\n]*(mg/dl)?", "mg/dL", "mg/dL", (3.5, 7.2)),
]


def _extract_local_patient_info(raw_text: str) -> PatientInfo:
    """Extract patient metadata locally so demographics never have to be sent as free text."""
    name_match = re.search(
        r"(?:patient\s+name|pt\.?\s*name|(?<!test\s)(?<!lab\s)(?<!assay\s)name)\s*[:|]\s*([A-Za-z][A-Za-z.\s'-]{1,45}?)(?=\r?\n|age|gender|sex|,|$)",
        raw_text,
        re.IGNORECASE,
    )
    if not name_match:
        name_match = re.search(
            r"\b(?:mr|mrs|ms|miss|smt|shri)\.?\s+([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})(?=\r?\n|,|\||age|gender|sex|s/o|d/o|$)",
            raw_text,
            re.IGNORECASE,
        )
    age_match = re.search(r"(?:age(?:\s*/\s*(?:sex|gender))?|yrs?|years?)\s*[:|]?\s*([0-9]{1,3})", raw_text, re.IGNORECASE)
    gender_match = re.search(r"\b(male|female|other)\b", raw_text, re.IGNORECASE)
    date_match = re.search(
        r"(?:report\s*date|collected(?:\s+on)?|date)\s*[:|]?\s*([0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{2,4}|[0-9]{1,2}-[A-Za-z]{3}-[0-9]{2,4})",
        raw_text,
        re.IGNORECASE,
    )
    lab_match = re.search(r"(metropolis|dr\s*lal(?:\s+pathlabs)?|apollo|quest|pathlabs|diagnostics|hospital|clinic)", raw_text, re.IGNORECASE)

    return PatientInfo(
        name=name_match.group(1).strip() if name_match else None,
        age=float(age_match.group(1)) if age_match else None,
        gender=gender_match.group(1).lower() if gender_match else None,
        report_date=date_match.group(1) if date_match else None,
        lab_name=lab_match.group(0).title() if lab_match else None,
    )


def _strip_inline_demographics(text: str) -> str:
    """Strip any stray inline age/sex/gender tags from minimized biomarker lines."""
    if not text:
        return text
    cleaned = re.sub(
        r"(?i)\b(?:age(?:\s*/\s*(?:sex|gender))?|gender|sex)\s*[:|]?\s*(?:\d{1,3}\s*(?:yrs?|years?)?(?:\s*/\s*[MF])?|male|female|other)\b",
        "[REDACTED_DEMOGRAPHIC]",
        text,
    )
    return cleaned


def heuristic_extract(raw_text: str, duration_ms: int = 50) -> ExtractionResponse:
    """Fallback rule-based extractor when no LLM API key is present."""
    patient_info = _extract_local_patient_info(raw_text)

    biomarkers = []
    extracted_canonical = set()
    low_confidence_count = 0

    lines = raw_text.splitlines()

    for std_id, disp_name, pattern, unit, std_unit, (ref_low, ref_high) in HEURISTIC_PATTERNS:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            try:
                val = float(match.group(1))
                # Unit normalization for WBC: if > 1000 cells/cumm, convert to 10^3/uL
                if std_id == "wbc" and val > 100:
                    val = round(val / 1000.0, 2)

                # Determine flag
                flag = BiomarkerFlag.NORMAL
                if ref_low is not None and val < ref_low:
                    flag = BiomarkerFlag.LOW
                elif ref_high is not None and val > ref_high:
                    flag = BiomarkerFlag.HIGH

                # Source line
                source_line = next((l.strip() for l in lines if match.group(0) in l), match.group(0))

                item = BiomarkerItem(
                    standard_id=CanonicalBiomarker(std_id),
                    display_name=disp_name,
                    raw_name=match.group(0).split(":")[0].strip() if ":" in match.group(0) else disp_name,
                    value=val,
                    unit=unit,
                    standard_unit=std_unit,
                    reference_range=ReferenceRange(low=ref_low, high=ref_high, text=f"{ref_low} - {ref_high} {unit}"),
                    confidence=0.92,
                    flag=flag,
                    needs_review=False,
                    source_text=source_line,
                )
                biomarkers.append(item)
                extracted_canonical.add(std_id)
            except Exception as e:
                logger.debug(f"Failed parsing matched value for {std_id}: {e}")

    # Pass 2: Multi-line OCR association for markers missed by single-line regexes.
    _OCR_RANGE_RE = re.compile(
        r"^\s*\d+(?:\.\d+)?\s*[-–·]\s*\d+(?:\.\d+)?(?:\s*[A-Za-z/%^0-9]*)?\s*$"
    )
    _OCR_UNIT_COMPAT_RE = re.compile(
        r"(?i)^\s*(?:10[\^±-]?\s*3/[uµμ]?l|103/[uµμ]?l|mg/dl|g/dl|g/l|mmol/l|umol/l|"
        r"mg/l|iu/l|u/l|fl|pg|meq/l|cells/(?:cumm|[uµμ]l)|/(?:cumm|[uµμ]l)|%)\s*$"
    )
    _OCR_SCALAR_RE = re.compile(
        r"(?i)^\s*[<>~]?\s*(\d+(?:\.\d+)?)\s*("
        r"mg/dl|g/dl|g/l|mmol/l|umol/l|mg/l|iu/l|u/l|fl|pg|meq/l|"
        r"10[\^±-]?\s*3/[uµμ]?l|103/[uµμ]?l|cells/(?:cumm|[uµμ]l)|/(?:cumm|[uµμ]l)|%"
        r")?\s*$"
    )
    _UNIT_FAMILY = {
        "albumin": {"g/dl", "g/l"},
        "creatinine": {"mg/dl", "umol/l"},
        "glucose_fasting": {"mg/dl", "mmol/l"},
        "crp": {"mg/l", "mg/dl"},
        "lymphocyte_pct": {"%"},
        "mcv": {"fl"},
        "rdw": {"%"},
        "alp": {"u/l", "iu/l"},
        "wbc": {"10^3/ul", "10^9/l", "103/ul", "10±3/ul", "10-3/ul", "cells/cumm", "/cumm"},
        "hemoglobin": {"g/dl"},
        "platelets": {"10^3/ul", "103/ul", "10±3/ul", "10-3/ul", "cells/cumm", "/cumm", "lakh/cumm"},
        "hba1c": {"%"},
        "cholesterol_total": {"mg/dl"},
        "cholesterol_hdl": {"mg/dl"},
        "cholesterol_ldl": {"mg/dl"},
        "triglycerides": {"mg/dl"},
        "bilirubin_total": {"mg/dl"},
        "ast_sgot": {"u/l", "iu/l"},
        "alt_sgpt": {"u/l", "iu/l"},
        "bun": {"mg/dl"},
        "uric_acid": {"mg/dl"},
    }

    spec_by_id = {s[0]: s for s in HEURISTIC_PATTERNS}
    line_units: Dict[int, str] = {}
    line_scalars: Dict[int, Tuple[float, Optional[str]]] = {}
    alias_hits: list[Tuple[int, str]] = []

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or _NON_RESULT_CONTEXT_LINE.search(stripped):
            continue
        if _STANDALONE_UNIT_REGEX.match(stripped) or _OCR_UNIT_COMPAT_RE.match(stripped):
            line_units[idx] = stripped.lower().replace(" ", "")
            continue
        if _OCR_RANGE_RE.match(stripped):
            continue
        sm = _OCR_SCALAR_RE.match(stripped)
        if sm:
            line_scalars[idx] = (float(sm.group(1)), sm.group(2).lower() if sm.group(2) else None)

        lower_line = stripped.lower()
        for std_id in spec_by_id:
            if std_id in extracted_canonical:
                continue
            # Avoid matching cholesterol_total on HDL/LDL lines
            if std_id == "cholesterol_total" and ("hdl" in lower_line or "ldl" in lower_line or "vldl" in lower_line):
                continue
            aliases = BIOMARKER_ALIASES.get(std_id, ())
            matched_alias = any(
                re.search(rf"(?i)(?<![A-Za-z0-9]){re.escape(a).replace(r'\ ', r'\s+')}(?![A-Za-z0-9])", stripped)
                for a in aliases
            )
            if matched_alias:
                alias_hits.append((idx, std_id))

    claimed_scalar_lines = set()
    pending = list(alias_hits)

    def _plausible_candidates(alias_idx: int, std_id: str) -> list[Tuple[int, int, float, bool]]:
        canon = CanonicalBiomarker(std_id)
        low_lim, high_lim = PHYSIOLOGICAL_LIMITS.get(canon, (0.0, 1e9))
        expected_units = _UNIT_FAMILY.get(std_id, set())
        out = []
        for cand_idx in range(max(0, alias_idx - 2), min(len(lines), alias_idx + 3)):
            if cand_idx in claimed_scalar_lines or cand_idx not in line_scalars:
                continue
            raw_val, inline_unit = line_scalars[cand_idx]
            val = raw_val / 1000.0 if (std_id in ("wbc", "platelets") and raw_val > 1500) else raw_val
            if val < low_lim or val > high_lim:
                continue
            nearby_unit = inline_unit or line_units.get(cand_idx + 1) or line_units.get(cand_idx - 1) or line_units.get(alias_idx + 1)
            unit_match = bool(nearby_unit and any(u in nearby_unit for u in expected_units))
            # Reject explicit contradictory unit right next to the candidate
            if inline_unit and expected_units and not any(u in inline_unit for u in expected_units):
                continue
            dist = abs(cand_idx - alias_idx)
            # Score: higher is better (unit match + closer distance + post-alias preference)
            score = (10 if unit_match else 0) + (5 - dist) * 2 + (1 if cand_idx > alias_idx else 0)
            out.append((score, cand_idx, val, unit_match))
        out.sort(key=lambda t: (-t[0], t[1]))
        return out

    # Iterative assignment: resolve unique 1-candidate aliases before scored ones; never guess ties.
    for pass_num in range(2):
        next_pending = []
        for alias_idx, std_id in pending:
            if std_id in extracted_canonical:
                continue
            cands = _plausible_candidates(alias_idx, std_id)
            if not cands:
                continue
            if pass_num == 0 and len(cands) > 1:
                next_pending.append((alias_idx, std_id))
                continue

            _, disp_name, _, unit, std_unit, (ref_low, ref_high) = spec_by_id[std_id]
            top_score = cands[0][0]
            tied_top = [c for c in cands if c[0] == top_score]

            if len(tied_top) > 1:
                # Ambiguous tie: mark needs_review and never guess the numeric value.
                item = BiomarkerItem(
                    standard_id=CanonicalBiomarker(std_id),
                    display_name=disp_name,
                    raw_name=lines[alias_idx].strip()[:60],
                    value=None,
                    unit=unit,
                    standard_unit=std_unit,
                    reference_range=ReferenceRange(low=ref_low, high=ref_high, text=f"{ref_low} - {ref_high} {unit}"),
                    confidence=0.0,
                    flag=BiomarkerFlag.UNKNOWN,
                    needs_review=True,
                    source_text=lines[alias_idx].strip(),
                )
                biomarkers.append(item)
                extracted_canonical.add(std_id)
                low_confidence_count += 1
                continue

            _, chosen_idx, val, unit_match = cands[0]
            claimed_scalar_lines.add(chosen_idx)
            flag = BiomarkerFlag.NORMAL
            if ref_low is not None and val < ref_low:
                flag = BiomarkerFlag.LOW
            elif ref_high is not None and val > ref_high:
                flag = BiomarkerFlag.HIGH

            conf = 0.74 if (len(cands) == 1 and unit_match) else 0.65
            item = BiomarkerItem(
                standard_id=CanonicalBiomarker(std_id),
                display_name=disp_name,
                raw_name=lines[alias_idx].strip()[:60],
                value=val,
                unit=unit,
                standard_unit=std_unit,
                reference_range=ReferenceRange(low=ref_low, high=ref_high, text=f"{ref_low} - {ref_high} {unit}"),
                confidence=conf,
                flag=flag,
                needs_review=True,
                source_text=f"{lines[alias_idx].strip()} -> {lines[chosen_idx].strip()}",
            )
            biomarkers.append(item)
            extracted_canonical.add(std_id)
            low_confidence_count += 1
        pending = next_pending

    missing_phenoage = sorted(list(PHENOAGE_CORE_BIOMARKERS - extracted_canonical))

    meta = ExtractionMetadata(
        model_used="heuristic-rule-engine (offline)",
        extraction_duration_ms=duration_ms,
        raw_text_length=len(raw_text),
        total_biomarkers_found=len(biomarkers),
        low_confidence_count=low_confidence_count,
        missing_phenoage_biomarkers=missing_phenoage,
    )

    return ExtractionResponse(
        patient_info=patient_info,
        biomarkers=biomarkers,
        extraction_metadata=meta,
    )


def call_openrouter_api(model: str, prompt: str, api_key: str, timeout: float = 30.0) -> str:
    """Call OpenRouter completions endpoint with fail-closed redaction and data-collection opt-out."""
    # Final fail-closed PII redaction right before constructing outbound payload.
    safe_prompt, _ = redact_pii(prompt)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/SanchitKRai/Healthspan-Passport",
        "X-Title": "Healthspan Passport",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": safe_prompt},
        ],
        "temperature": 0.0,
        "max_tokens": 2000,
        # Request no prompt/completion data collection (OpenRouter provider routing docs).
        "provider": {"data_collection": "deny"},
    }
    if "kimi-k2" not in model.lower():
        payload["response_format"] = {"type": "json_object"}

    with httpx.Client(timeout=timeout) as client:
        resp = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
        resp.raise_for_status()
        res_json = resp.json()
        content = (res_json.get("choices") or [{}])[0].get("message", {}).get("content")
        if not isinstance(content, str) or not content.strip():
            raise ValueError(f"OpenRouter returned empty content for {model}")
        return content


def prepare_outbound_extraction_text(raw_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Shared outbound payload builder: minimize raw_text to biomarker/unit lines,
    redact PII, and strip inline demographic fragments so preview and OpenRouter
    extraction produce the exact same text.
    """
    minimized_text, min_stats = minimize_to_result_lines(raw_text)
    if not minimized_text.strip():
        return "", {
            "total_lines": min_stats.get("total_lines", 0),
            "matched_lines": 0,
            "kept_lines": 0,
            "redacted_categories": [],
        }

    redacted_text, redaction_counts = redact_pii(minimized_text)
    redacted_text = _strip_inline_demographics(redacted_text)
    return redacted_text, {
        "total_lines": min_stats.get("total_lines", 0),
        "matched_lines": min_stats.get("matched_lines", 0),
        "kept_lines": min_stats.get("kept_lines", 0),
        "redacted_categories": sorted(redaction_counts.keys()),
    }


def extract_biomarkers_with_llm(
    raw_text: str,
    api_key: Optional[str] = None,
    primary_model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    allow_cloud_llm: bool = False,
) -> ExtractionResponse:
    """
    Main extraction pipeline:
    1. If cloud LLM consent is not granted (allow_cloud_llm=False) or no API key is set,
       run local heuristic extraction only (no outbound network call).
    2. Extract structured patient metadata locally, minimize raw_text to biomarker/unit
       result lines, and redact PII BEFORE constructing prompts (fail-closed).
       If minimization leaves zero lines, skip OpenRouter and fall back locally.
    3. Try Primary Model (mistralai/mistral-small-3.2-24b-instruct) with 1 JSON retry
       (or an explicit env override / fallback_model if configured).
    4. Merge locally extracted structured demographics onto the response and fall back
       to the local heuristic engine if the cloud call fails.
    """
    if not allow_cloud_llm:
        logger.info("Cloud LLM consent not granted (allow_cloud_llm=False). Using local heuristic extraction engine.")
        res = heuristic_extract(raw_text)
        res.extraction_metadata.model_used = "heuristic-rule-engine (local-only)"
        return res

    api_key = api_key or os.getenv("OPENROUTER_API_KEY")
    primary = primary_model or os.getenv("OPENROUTER_PRIMARY_MODEL", PRIMARY_MODEL)
    fallback = fallback_model if fallback_model is not None else FALLBACK_MODEL

    if not api_key:
        logger.info("No OPENROUTER_API_KEY set. Using local heuristic extraction engine.")
        return heuristic_extract(raw_text)

    local_patient = _extract_local_patient_info(raw_text)

    redacted_text, prep_stats = prepare_outbound_extraction_text(raw_text)
    if not redacted_text.strip():
        logger.info(
            "Minimization retained 0/%s lines; skipping outbound OpenRouter call and falling back locally.",
            prep_stats.get("total_lines", 0),
        )
        res = heuristic_extract(raw_text)
        res.extraction_metadata.model_used = "heuristic-rule-engine (minimized-zero-lines-local-fallback)"
        return res

    logger.info(
        "Prepared outbound OpenRouter text: kept_lines=%s/%s redacted_categories=%s",
        prep_stats.get("kept_lines", 0),
        prep_stats.get("total_lines", 0),
        prep_stats.get("redacted_categories", []),
    )

    start_time = time.time()
    prompt = build_extraction_prompt(redacted_text)

    def _merge_local_patient_fields(resp: ExtractionResponse) -> ExtractionResponse:
        for field in ("name", "age", "gender", "report_date", "lab_name"):
            local_val = getattr(local_patient, field)
            if local_val is not None:
                setattr(resp.patient_info, field, local_val)
        return resp

    # 1. Try Primary Model (plus optional explicit fallback override if supplied)
    for model_candidate in [m for m in (primary, fallback) if m]:
        try:
            logger.info("Extracting biomarkers with model: %s", model_candidate)
            raw_response = call_openrouter_api(model_candidate, prompt, api_key)
            duration_ms = int((time.time() - start_time) * 1000)

            # Try parsing
            try:
                parsed = parse_and_validate_extraction(raw_response, redacted_text, model_candidate, duration_ms)
                return _merge_local_patient_fields(parsed)
            except Exception as parse_err:
                logger.warning(
                    "Validation failed on %s output (%s). Initiating 1 retry.",
                    model_candidate,
                    type(parse_err).__name__,
                )
                # One retry with schema error class only (never echo raw values)
                retry_prompt = build_retry_prompt(redacted_text, type(parse_err).__name__)
                retry_response = call_openrouter_api(model_candidate, retry_prompt, api_key)
                duration_ms = int((time.time() - start_time) * 1000)
                parsed_retry = parse_and_validate_extraction(
                    retry_response, redacted_text, f"{model_candidate} (retry)", duration_ms
                )
                return _merge_local_patient_fields(parsed_retry)

        except Exception as model_err:
            logger.error("Error calling %s: %s", model_candidate, type(model_err).__name__)
            # Loop will continue to fallback model

    # If both models fail, use heuristic engine with warning
    logger.warning("All OpenRouter models failed. Falling back to heuristic extractor.")
    duration_ms = int((time.time() - start_time) * 1000)
    res = heuristic_extract(raw_text, duration_ms)
    res.extraction_metadata.model_used = "heuristic-rule-engine (api-fallback)"
    return res
