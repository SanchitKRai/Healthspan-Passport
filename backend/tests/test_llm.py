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
    assert "albumin" in response.extraction_metadata.missing_phenoage_biomarkers


def test_parse_json_invalid_raises():
    from app.llm.client import parse_and_validate_extraction
    with pytest.raises(Exception):
        parse_and_validate_extraction("Invalid non-json text", raw_text="...", model_name="test-model", duration_ms=100)


def test_parse_null_and_non_float_strings_gracefully():
    from app.llm.client import parse_and_validate_extraction
    # Tests issue I2: null patient_info, null biomarkers, string with "<0.5"
    payload = {
        "patient_info": None,
        "biomarkers": [
            {
                "standard_id": "crp",
                "display_name": "C-Reactive Protein",
                "raw_name": "hs-CRP",
                "value": "<0.5",
                "unit": "mg/L",
                "confidence": 0.9,
                "flag": "normal"
            }
        ]
    }
    resp = parse_and_validate_extraction(json.dumps(payload), raw_text="...", model_name="test", duration_ms=100)
    assert resp.patient_info.name is None
    assert len(resp.biomarkers) == 1
    assert resp.biomarkers[0].value == 0.5


def test_llm_retry_on_malformed_json():
    # Tests issue I4: 1 retry on malformed JSON
    from app.llm.client import extract_biomarkers_with_llm
    
    valid_payload = json.dumps({
        "patient_info": {"name": "Test User"},
        "biomarkers": [{"standard_id": "albumin", "value": 4.5, "unit": "g/dL"}]
    })
    
    with patch("app.llm.client.call_openrouter_api") as mock_api:
        mock_api.side_effect = ["NOT VALID JSON", valid_payload]
        res = extract_biomarkers_with_llm("Serum Albumin: 4.5 g/dL", api_key="sk-test-key", allow_cloud_llm=True)
        assert mock_api.call_count == 2
        assert "(retry)" in res.extraction_metadata.model_used
        assert len(res.biomarkers) == 1


def test_llm_fallback_to_secondary_model():
    # Tests issue I4: Fallback to secondary model if primary raises HTTP error
    from app.llm.client import extract_biomarkers_with_llm
    
    valid_payload = json.dumps({
        "patient_info": {"name": "Fallback User"},
        "biomarkers": [{"standard_id": "glucose_fasting", "value": 90.0, "unit": "mg/dL"}]
    })
    
    with patch("app.llm.client.call_openrouter_api") as mock_api:
        mock_api.side_effect = [RuntimeError("Primary model 500 error"), valid_payload]
        res = extract_biomarkers_with_llm(
            "Fasting Glucose: 90 mg/dL",
            api_key="sk-test-key",
            primary_model="nemotron",
            fallback_model="kimi",
            allow_cloud_llm=True,
        )
        assert mock_api.call_count == 2
        assert res.extraction_metadata.model_used == "kimi"
        assert res.patient_info.name == "Fallback User"


def test_llm_consent_gating_blocks_outbound_calls():
    from app.llm.client import extract_biomarkers_with_llm

    with patch("app.llm.client.call_openrouter_api") as mock_api:
        res = extract_biomarkers_with_llm(
            "Patient Name: Priya Nair\nFasting Glucose: 102 mg/dL",
            api_key="sk-test-key",
        )
        assert mock_api.call_count == 0
        assert "local-only" in res.extraction_metadata.model_used
        assert any(b.standard_id == "glucose_fasting" and b.value == 102.0 for b in res.biomarkers)


def test_llm_redacts_pii_before_outbound_call():
    from app.llm.client import extract_biomarkers_with_llm

    raw_report = (
        "Patient Name: Priya Nair\n"
        "Phone: +91 9811122233\n"
        "Email: priya.nair@example.com\n"
        "Aadhaar: 4321 8765 1234\n"
        "DOB: 1985-06-12\n"
        "Fasting Glucose: 102 mg/dL\n"
    )
    valid_payload = json.dumps({
        "patient_info": {},
        "biomarkers": [{"standard_id": "glucose_fasting", "value": 102.0, "unit": "mg/dL"}]
    })

    with patch("app.llm.client.call_openrouter_api", return_value=valid_payload) as mock_api:
        extract_biomarkers_with_llm(raw_report, api_key="sk-test-key", allow_cloud_llm=True)
        assert mock_api.call_count == 1
        sent_prompt = mock_api.call_args[0][1]
        assert "Priya Nair" not in sent_prompt
        assert "9811122233" not in sent_prompt
        assert "priya.nair@example.com" not in sent_prompt
        assert "4321 8765 1234" not in sent_prompt
        assert "1985-06-12" not in sent_prompt
        assert "102" in sent_prompt


def test_heuristic_regex_does_not_bleed_across_lines():
    # Tests issue C1: regex whitespace shouldn't cross newlines and capture reference ranges
    from app.llm.client import heuristic_extract
    ocr_tabular_text = """
    INVESTIGATION    VALUE    UNIT      REF RANGE
    WBC Count        6.5      10^3/uL   4.0 - 11.0
    Hemoglobin       13.1     g/dL      12.0 - 15.5
    MCV              89.0     fL        80.0 - 100.0
    RDW-CV           13.0     %         11.5 - 14.5
    """
    res = heuristic_extract(ocr_tabular_text)
    hb = next((b for b in res.biomarkers if b.standard_id == "hemoglobin"), None)
    rdw = next((b for b in res.biomarkers if b.standard_id == "rdw"), None)
    assert hb is not None
    assert hb.value == 13.1
    assert rdw is not None
    assert rdw.value == 13.0
