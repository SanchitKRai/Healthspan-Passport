import pytest
import json
from unittest.mock import patch, MagicMock


def test_build_extraction_prompt():
    from app.llm.prompts import build_extraction_prompt
    raw_text = "Patient: John Doe, Age: 42, Glucose: 95 mg/dL"
    prompt = build_extraction_prompt(raw_text)
    assert "John Doe" in prompt
    assert "standard_id" in prompt
    assert "PhenoAge" in prompt or "albumin" in prompt


def test_parse_and_validate_json_success():
    from app.llm.client import parse_and_validate_extraction
    valid_payload = {
        "patient_info": {
            "name": "Jane Doe",
            "age": 35,
            "gender": "female",
            "report_date": "2026-11-20",
            "lab_name": "Apollo Diagnostics"
        },
        "biomarkers": [
            {
                "standard_id": "glucose_fasting",
                "display_name": "Fasting Blood Sugar",
                "raw_name": "Fasting Glucose",
                "value": 88.0,
                "unit": "mg/dL",
                "standard_unit": "mg/dL",
                "confidence": 0.95,
                "flag": "normal",
                "needs_review": False,
                "source_text": "Fasting Glucose: 88 mg/dL"
            }
        ]
    }
    json_text = f"Here is the result:\n```json\n{json.dumps(valid_payload)}\n```"
    response = parse_and_validate_extraction(json_text, raw_text="...", model_name="test-model", duration_ms=200)
    assert response.patient_info.name == "Jane Doe"
    assert len(response.biomarkers) == 1
    assert response.biomarkers[0].standard_id == "glucose_fasting"
    assert response.extraction_metadata.model_used == "test-model"
    # PhenoAge missing markers should be computed
    assert "albumin" in response.extraction_metadata.missing_phenoage_biomarkers


def test_parse_json_invalid_raises():
    from app.llm.client import parse_and_validate_extraction
    with pytest.raises(Exception):
        parse_and_validate_extraction("Invalid non-json text", raw_text="...", model_name="test-model", duration_ms=100)


def test_heuristic_fallback_when_no_api_key():
    from app.llm.client import extract_biomarkers_with_llm
    sample_text = """
    Patient Name: Suresh Patel
    Age: 52 Years
    Gender: Male
    Date: 15-Nov-2026
    Lab: Metropolis Healthcare
    
    TEST NAME                VALUE     UNIT        REFERENCE
    Serum Albumin            4.1       g/dL        3.5 - 5.0
    Serum Creatinine         1.0       mg/dL       0.7 - 1.3
    Fasting Blood Glucose    105       mg/dL       70 - 99
    hs-CRP                   2.4       mg/L        0.0 - 1.0
    WBC Count                6800      cells/cumm  4000 - 11000
    """
    # Without API key, extract_biomarkers_with_llm should use heuristic fallback
    with patch.dict("os.environ", {}, clear=True):
        res = extract_biomarkers_with_llm(sample_text)
        assert res.patient_info.name == "Suresh Patel"
        assert res.patient_info.age == 52.0
        assert len(res.biomarkers) >= 3
        # Fasting glucose 105 is > 99, so flag should be high
        glucose = next((b for b in res.biomarkers if b.standard_id == "glucose_fasting"), None)
        assert glucose is not None
        assert glucose.value == 105.0
