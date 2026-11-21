import io
import pytest
import pdfplumber
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.biomarker import (
    ClinicalExportRequest,
    PatientInfo,
    BiomarkerItem,
    BiomarkerFlag,
    CanonicalBiomarker,
    ReferenceRange,
    PhenoAgeResult,
    RiskFlagItem,
)


@pytest.fixture
def sample_export_request() -> ClinicalExportRequest:
    return ClinicalExportRequest(
        patient_info=PatientInfo(
            name="Rahul Sharma",
            age=45.0,
            gender="male",
            report_date="2026-03-15",
            lab_name="Metropolis Healthcare"
        ),
        chronological_age=45.0,
        patient_gender="male",
        phenoage=PhenoAgeResult(
            is_valid=True,
            phenoage=48.2,
            age_acceleration=3.2,
            mortality_score_10yr=0.048,
            missing_markers=[],
            message="PhenoAge computed successfully."
        ),
        biomarkers=[
            BiomarkerItem(
                standard_id=CanonicalBiomarker.GLUCOSE_FASTING,
                display_name="Fasting Glucose",
                raw_name="Fasting Glucose",
                value=114.0,
                unit="mg/dL",
                standard_unit="mmol/L",
                reference_range=ReferenceRange(low=70.0, high=99.0),
                confidence=0.98,
                flag=BiomarkerFlag.HIGH
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.CRP,
                display_name="hs-CRP",
                raw_name="hs-CRP",
                value=3.2,
                unit="mg/L",
                standard_unit="mg/dL",
                reference_range=ReferenceRange(low=0.0, high=1.0),
                confidence=0.95,
                flag=BiomarkerFlag.HIGH
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.ALBUMIN,
                display_name="Serum Albumin",
                raw_name="Serum Albumin",
                value=4.2,
                unit="g/dL",
                standard_unit="g/L",
                reference_range=ReferenceRange(low=3.5, high=5.2),
                confidence=0.99,
                flag=BiomarkerFlag.NORMAL
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.CREATININE,
                display_name="Serum Creatinine",
                raw_name="Creatinine",
                value=0.95,
                unit="mg/dL",
                standard_unit="µmol/L",
                reference_range=ReferenceRange(low=0.7, high=1.3),
                confidence=0.97,
                flag=BiomarkerFlag.NORMAL
            ),
            BiomarkerItem(
                standard_id=CanonicalBiomarker.WBC,
                display_name="WBC Count",
                raw_name="Total Leukocyte Count",
                value=7.8,
                unit="10^3/µL",
                standard_unit="10^9/L",
                reference_range=ReferenceRange(low=4.0, high=10.0),
                confidence=0.96,
                flag=BiomarkerFlag.NORMAL
            ),
        ],
        risk_flags=[
            RiskFlagItem(
                category="metabolic",
                title="Impaired Fasting Glucose (Pre-diabetes)",
                status="borderline",
                markers=["glucose_fasting"],
                message="Fasting glucose is in pre-diabetic range (100-125 mg/dL).",
                recommendation="Evaluate HbA1c and review carbohydrate quality with clinician."
            ),
            RiskFlagItem(
                category="inflammation",
                title="Elevated Systemic Inflammation",
                status="elevated",
                markers=["crp"],
                message="hs-CRP is elevated (> 3.0 mg/L).",
                recommendation="Investigate vascular or metabolic inflammatory triggers."
            ),
        ],
        questions_for_doctor=[
            "Based on these fasting glucose numbers, should we measure HbA1c to evaluate glycemic control?",
            "Given the elevated hs-CRP (3.2 mg/L), do you advise assessing an ApoB or lipid particle count?",
            "What lifestyle interventions and testing timeline (e.g., 90 days) do you suggest before medication?"
        ]
    )


def test_generate_clinician_pdf_single_page(sample_export_request: ClinicalExportRequest):
    from app.core.exporter import generate_clinician_pdf

    pdf_bytes = generate_clinician_pdf(sample_export_request)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-")

    # Strict constraint: Must fit on exactly 1 single page without overflow
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        assert len(pdf.pages) == 1
        page_text = pdf.pages[0].extract_text()
        assert "Healthspan Passport" in page_text
        assert "Rahul Sharma" in page_text
        assert "Fasting Glucose" in page_text
        assert "48.2" in page_text or "PhenoAge" in page_text


def test_generate_fhir_r4_bundle(sample_export_request: ClinicalExportRequest):
    from app.core.exporter import generate_fhir_bundle

    bundle = generate_fhir_bundle(sample_export_request)
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert "entry" in bundle
    assert len(bundle["entry"]) >= 5

    # Check LOINC codes are mapped
    loinc_codes = []
    for entry in bundle["entry"]:
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Observation":
            coding = resource.get("code", {}).get("coding", [])
            for c in coding:
                if c.get("system") == "http://loinc.org":
                    loinc_codes.append(c.get("code"))

    assert "1558-6" in loinc_codes  # Fasting glucose
    assert "30522-7" in loinc_codes  # hs-CRP
    assert "1751-7" in loinc_codes  # Albumin


def test_api_export_pdf_endpoint(sample_export_request: ClinicalExportRequest):
    client = TestClient(app)
    response = client.post("/api/export/pdf", json=sample_export_request.model_dump())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert len(response.content) > 1000
    assert response.content.startswith(b"%PDF-")


def test_api_export_fhir_endpoint(sample_export_request: ClinicalExportRequest):
    client = TestClient(app)
    response = client.post("/api/export/fhir", json=sample_export_request.model_dump())
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    data = response.json()
    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
