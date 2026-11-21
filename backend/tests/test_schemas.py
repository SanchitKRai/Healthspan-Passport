import pytest
from pydantic import ValidationError

def test_biomarker_schema_validation():
    from app.schemas.biomarker import (
        BiomarkerItem,
        PatientInfo,
        ExtractionResponse,
        ExtractionMetadata,
        CanonicalBiomarker,
        BiomarkerFlag,
    )

    # Valid PatientInfo
    patient = PatientInfo(
        name="Ramesh Kumar",
        age=45.0,
        gender="male",
        report_date="2026-11-20",
        lab_name="Dr Lal PathLabs"
    )
    assert patient.name == "Ramesh Kumar"
    assert patient.age == 45.0

    # Valid BiomarkerItem
    bio = BiomarkerItem(
        standard_id=CanonicalBiomarker.ALBUMIN,
        display_name="Serum Albumin",
        raw_name="S. Albumin",
        value=4.2,
        unit="g/dL",
        standard_unit="g/dL",
        reference_range={"low": 3.5, "high": 5.2, "text": "3.5 - 5.2 g/dL"},
        confidence=0.98,
        flag=BiomarkerFlag.NORMAL,
        needs_review=False,
        source_text="Serum Albumin: 4.2 g/dL (3.5 - 5.2)"
    )
    assert bio.standard_id == CanonicalBiomarker.ALBUMIN
    assert bio.value == 4.2
    assert bio.needs_review is False

    # Low confidence triggers needs_review
    bio_low = BiomarkerItem(
        standard_id=CanonicalBiomarker.CRP,
        display_name="C-Reactive Protein",
        raw_name="hs-CRP",
        value=1.5,
        unit="mg/L",
        standard_unit="mg/L",
        confidence=0.65,
        flag=BiomarkerFlag.NORMAL,
        needs_review=False # Validator should auto-set to True because confidence < 0.8
    )
    assert bio_low.needs_review is True

    # Complete ExtractionResponse
    meta = ExtractionMetadata(
        model_used="nvidia/llama-3.1-nemotron-70b-instruct",
        extraction_duration_ms=450,
        raw_text_length=1200,
        total_biomarkers_found=1,
        low_confidence_count=1,
        missing_phenoage_biomarkers=["creatinine", "glucose_fasting"]
    )
    resp = ExtractionResponse(
        patient_info=patient,
        biomarkers=[bio, bio_low],
        extraction_metadata=meta
    )
    assert len(resp.biomarkers) == 2
    assert "creatinine" in resp.extraction_metadata.missing_phenoage_biomarkers

def test_physiological_limit_validation():
    from app.schemas.biomarker import BiomarkerItem, CanonicalBiomarker, BiomarkerFlag

    # Glucose 1500 mg/dL is biologically implausible / extreme crisis
    bio_extreme = BiomarkerItem(
        standard_id=CanonicalBiomarker.GLUCOSE_FASTING,
        display_name="Fasting Glucose",
        raw_name="Glucose",
        value=1500.0,
        unit="mg/dL",
        standard_unit="mg/dL",
        confidence=0.95,
        flag=BiomarkerFlag.HIGH,
        needs_review=False
    )
    # Validator must enforce needs_review = True and flag = CRITICAL
    assert bio_extreme.needs_review is True
    assert bio_extreme.flag == BiomarkerFlag.CRITICAL

    # Albumin 25 g/dL (normal is ~3.5-5.0, plausible upper bound ~8.0)
    bio_albumin = BiomarkerItem(
        standard_id=CanonicalBiomarker.ALBUMIN,
        display_name="Serum Albumin",
        raw_name="Albumin",
        value=25.0,
        unit="g/dL",
        standard_unit="g/dL",
        confidence=0.99,
        flag=BiomarkerFlag.HIGH,
        needs_review=False
    )
    assert bio_albumin.needs_review is True
    assert bio_albumin.flag == BiomarkerFlag.CRITICAL
