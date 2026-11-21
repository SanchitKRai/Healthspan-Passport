import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.schemas.biomarker import (
    ExplanationRequest,
    ExplanationResponse,
    RiskFlagItem,
    BiomarkerItem,
    BiomarkerFlag,
    CanonicalBiomarker,
)


def test_bilingual_explanation_generation():
    from app.core.explainer import generate_bilingual_explanation

    req = ExplanationRequest(
        chronological_age=45.0,
        patient_gender="male",
        phenoage=48.5,
        age_acceleration=3.5,
        risk_flags=[
            RiskFlagItem(
                category="metabolic",
                title="Impaired Fasting Glucose / Pre-diabetes",
                status="borderline",
                markers=["glucose_fasting"],
                message="Fasting blood glucose is in the pre-diabetic range.",
                recommendation="Review with physician and monitor glycemic response."
            ),
            RiskFlagItem(
                category="inflammation",
                title="Elevated Systemic Inflammation",
                status="elevated",
                markers=["crp"],
                message="hs-CRP is elevated (> 3.0 mg/L).",
                recommendation="Investigate lifestyle or inflammatory drivers."
            ),
        ],
        biomarkers=[
            BiomarkerItem(
                standard_id=CanonicalBiomarker.GLUCOSE_FASTING,
                display_name="Fasting Glucose",
                raw_name="Fasting Glucose",
                value=112.0,
                unit="mg/dL",
                standard_unit="mg/dL",
                flag=BiomarkerFlag.HIGH
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.CRP,
                display_name="hs-CRP",
                raw_name="hs-CRP",
                value=3.4,
                unit="mg/L",
                standard_unit="mg/L",
                flag=BiomarkerFlag.HIGH
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.ALBUMIN,
                display_name="Serum Albumin",
                raw_name="Serum Albumin",
                value=4.1,
                unit="g/dL",
                standard_unit="g/dL",
                flag=BiomarkerFlag.NORMAL
            ),
        ]
    )

    resp: ExplanationResponse = generate_bilingual_explanation(req)

    # English checks
    assert len(resp.summary_en) > 50
    assert "48.5" in resp.summary_en or "biological age" in resp.summary_en.lower()
    assert len(resp.key_findings_en) >= 2
    assert len(resp.dietary_guidance_en) >= 2
    assert 3 <= len(resp.questions_for_doctor_en) <= 6
    assert "physician" in resp.disclaimer_en.lower() or "doctor" in resp.disclaimer_en.lower()

    # Hindi checks
    assert len(resp.summary_hi) > 50
    assert any("\u0900" <= c <= "\u097F" for c in resp.summary_hi)  # Contains Hindi / Devanagari characters
    assert len(resp.key_findings_hi) >= 2
    assert len(resp.dietary_guidance_hi) >= 2
    assert len(resp.questions_for_doctor_hi) >= 3

    # Indian vegetarian nutrition guidance
    combined_diet = " ".join(resp.dietary_guidance_en).lower()
    assert any(w in combined_diet for w in ["millet", "dal", "protein", "carbohydrate", "fiber", "refined"])

    # Strict non-diagnostic check
    assert "you have diabetes" not in resp.summary_en.lower()
    assert "diagnosed with" not in resp.summary_en.lower()


def test_api_explain_endpoint():
    client = TestClient(app)
    payload = {
        "chronological_age": 52.0,
        "patient_gender": "female",
        "phenoage": 50.1,
        "age_acceleration": -1.9,
        "risk_flags": [],
        "biomarkers": [
            {
                "standard_id": "glucose_fasting",
                "display_name": "Fasting Glucose",
                "raw_name": "Fasting Glucose",
                "value": 92.0,
                "unit": "mg/dL",
                "standard_unit": "mg/dL",
                "flag": "normal",
                "needs_review": False
            }
        ]
    }
    response = client.post("/api/explain", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary_en" in data
    assert "summary_hi" in data
    assert len(data["dietary_guidance_en"]) > 0
    assert len(data["questions_for_doctor_hi"]) > 0
