import re
from typing import Dict, Any, Tuple, Optional

# Canonical target units for PhenoAge & routine analysis
# PhenoAge Levine (2018) canonical input units:
# Albumin: g/L
# Creatinine: µmol/L
# Glucose: mmol/L
# CRP: mg/dL
# Lymphocyte: %
# MCV: fL
# RDW: %
# ALP: U/L
# WBC: 10^9/L (or 10^3/µL)

INDIAN_REFERENCE_RANGES = {
    "glucose_fasting": {
        "mg/dL": {"low": 70.0, "high": 99.0, "text": "70 - 99 mg/dL (Normal Fasting)"},
        "mmol/L": {"low": 3.89, "high": 5.50, "text": "3.89 - 5.50 mmol/L"},
    },
    "hba1c": {
        "%": {"low": 4.0, "high": 5.6, "text": "4.0 - 5.6% (Non-diabetic)"},
    },
    "albumin": {
        "g/dL": {"low": 3.5, "high": 5.2, "text": "3.5 - 5.2 g/dL"},
        "g/L": {"low": 35.0, "high": 52.0, "text": "35 - 52 g/L"},
    },
    "creatinine": {
        "mg/dL": {
            "male": {"low": 0.7, "high": 1.3, "text": "0.7 - 1.3 mg/dL"},
            "female": {"low": 0.5, "high": 1.1, "text": "0.5 - 1.1 mg/dL"},
            "default": {"low": 0.6, "high": 1.2, "text": "0.6 - 1.2 mg/dL"},
        },
        "µmol/L": {
            "male": {"low": 62.0, "high": 115.0, "text": "62 - 115 µmol/L"},
            "female": {"low": 44.0, "high": 97.0, "text": "44 - 97 µmol/L"},
            "default": {"low": 53.0, "high": 106.0, "text": "53 - 106 µmol/L"},
        },
    },
    "crp": {
        "mg/L": {"low": 0.0, "high": 1.0, "text": "< 1.0 mg/L (Low cardiovascular risk)"},
        "mg/dL": {"low": 0.0, "high": 0.1, "text": "< 0.1 mg/dL"},
    },
    "lymphocyte_pct": {
        "%": {"low": 20.0, "high": 40.0, "text": "20 - 40%"},
    },
    "mcv": {
        "fL": {"low": 80.0, "high": 100.0, "text": "80 - 100 fL"},
    },
    "rdw": {
        "%": {"low": 11.5, "high": 14.5, "text": "11.5 - 14.5%"},
    },
    "alp": {
        "U/L": {"low": 44.0, "high": 147.0, "text": "44 - 147 U/L"},
    },
    "wbc": {
        "10^9/L": {"low": 4.0, "high": 11.0, "text": "4.0 - 11.0 10^9/L"},
        "10^3/uL": {"low": 4.0, "high": 11.0, "text": "4.0 - 11.0 10^3/uL"},
        "cells/cumm": {"low": 4000.0, "high": 11000.0, "text": "4000 - 11000 cells/cumm"},
    },
    "hemoglobin": {
        "g/dL": {
            "male": {"low": 13.0, "high": 17.0, "text": "13.0 - 17.0 g/dL"},
            "female": {"low": 12.0, "high": 15.0, "text": "12.0 - 15.0 g/dL"},
            "default": {"low": 12.0, "high": 16.0, "text": "12.0 - 16.0 g/dL"},
        }
    },
    "cholesterol_total": {
        "mg/dL": {"low": 125.0, "high": 200.0, "text": "< 200 mg/dL (Desirable)"},
    },
    "cholesterol_hdl": {
        "mg/dL": {
            "male": {"low": 40.0, "high": 60.0, "text": "> 40 mg/dL (Protective)"},
            "female": {"low": 50.0, "high": 70.0, "text": "> 50 mg/dL (Protective)"},
            "default": {"low": 40.0, "high": 60.0, "text": "40 - 60 mg/dL"},
        }
    },
    "cholesterol_ldl": {
        "mg/dL": {"low": 0.0, "high": 100.0, "text": "< 100 mg/dL (Optimal)"},
    },
    "triglycerides": {
        "mg/dL": {"low": 0.0, "high": 150.0, "text": "< 150 mg/dL (Desirable)"},
    },
    "bilirubin_total": {
        "mg/dL": {"low": 0.2, "high": 1.2, "text": "0.2 - 1.2 mg/dL"},
    },
    "ast_sgot": {
        "U/L": {"low": 10.0, "high": 40.0, "text": "10 - 40 U/L"},
    },
    "alt_sgpt": {
        "U/L": {"low": 7.0, "high": 56.0, "text": "7 - 56 U/L"},
    },
    "bun": {
        "mg/dL": {"low": 7.0, "high": 20.0, "text": "7 - 20 mg/dL"},
    },
    "uric_acid": {
        "mg/dL": {
            "male": {"low": 3.5, "high": 7.2, "text": "3.5 - 7.2 mg/dL"},
            "female": {"low": 2.6, "high": 6.0, "text": "2.6 - 6.0 mg/dL"},
            "default": {"low": 3.0, "high": 7.0, "text": "3.0 - 7.0 mg/dL"},
        }
    },
}


def clean_unit_str(unit: str) -> str:
    """Normalize unit string variations."""
    u = unit.lower().strip().replace(" ", "")
    u = u.replace("μ", "u").replace("µ", "u")
    return u


def get_reference_range(
    standard_id: str,
    unit: str,
    sex: Optional[str] = None
) -> Dict[str, Any]:
    """Retrieve Indian reference range for a biomarker and unit."""
    biomarker_refs = INDIAN_REFERENCE_RANGES.get(standard_id, {})
    # Match unit ignoring case
    matching_unit_key = next((k for k in biomarker_refs if clean_unit_str(k) == clean_unit_str(unit)), None)
    
    if not matching_unit_key:
        return {"low": None, "high": None, "text": None}

    ref_data = biomarker_refs[matching_unit_key]
    
    if "male" in ref_data or "female" in ref_data:
        s = (sex or "").lower()
        if s.startswith("m") and "male" in ref_data:
            return ref_data["male"]
        elif s.startswith("f") and "female" in ref_data:
            return ref_data["female"]
        return ref_data.get("default", {"low": None, "high": None, "text": None})

    return ref_data


def normalize_biomarker(
    standard_id: str,
    value: float,
    unit: str,
    sex: Optional[str] = None
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Normalize extracted biomarker value to canonical unit:
    - Albumin -> g/L (from g/dL: * 10)
    - Creatinine -> µmol/L (from mg/dL: * 88.4)
    - Glucose -> mmol/L (from mg/dL: / 18.0182)
    - CRP -> mg/dL (from mg/L: / 10; clamp min to 0.001 to avoid log(0))
    - WBC -> 10^9/L (from cells/cumm or /µL: / 1000)
    - Others -> validated canonical unit
    Returns: (normalized_value, canonical_unit, reference_range)
    """
    clean_u = clean_unit_str(unit)
    norm_val = value
    canon_unit = unit

    if standard_id == "albumin":
        if "g/dl" in clean_u:
            norm_val = value * 10.0
            canon_unit = "g/L"
        elif "g/l" in clean_u:
            norm_val = value
            canon_unit = "g/L"

    elif standard_id == "creatinine":
        if "mg/dl" in clean_u:
            norm_val = value * 88.4
            canon_unit = "µmol/L"
        elif "umol/l" in clean_u or "µmol/l" in clean_u:
            norm_val = value
            canon_unit = "µmol/L"

    elif standard_id in ["glucose_fasting", "glucose"]:
        if "mg/dl" in clean_u:
            norm_val = value / 18.0182
            canon_unit = "mmol/L"
        elif "mmol/l" in clean_u:
            norm_val = value
            canon_unit = "mmol/L"

    elif standard_id == "crp":
        # Clinical reports usually present hs-CRP in mg/L.
        # PhenoAge formula requires CRP in mg/dL: mg/L / 10 = mg/dL
        if "mg/l" in clean_u:
            norm_val = value / 10.0
            canon_unit = "mg/dL"
        elif "mg/dl" in clean_u:
            norm_val = value
            canon_unit = "mg/dL"
        # Safety floor for log calculation: CRP cannot be <= 0 in ln(CRP)
        norm_val = max(0.001, norm_val)

    elif standard_id == "wbc":
        if "cells/cumm" in clean_u or "/ul" in clean_u or "cells/ul" in clean_u:
            if value > 100:
                norm_val = value / 1000.0
            canon_unit = "10^9/L"
        elif "10^9/l" in clean_u or "10^3/ul" in clean_u or "x10^9/l" in clean_u:
            norm_val = value
            canon_unit = "10^9/L"

    elif standard_id == "lymphocyte_pct":
        canon_unit = "%"
    elif standard_id == "mcv":
        canon_unit = "fL"
    elif standard_id == "rdw":
        canon_unit = "%"
    elif standard_id == "alp":
        canon_unit = "U/L"

    ref_range = get_reference_range(standard_id, canon_unit, sex=sex)
    return round(norm_val, 4), canon_unit, ref_range
