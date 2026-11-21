import pytest


def test_phenoage_calculation_reference_case():
    from app.core.phenoage import calculate_phenoage

    biomarkers = {
        "albumin": 45.0,        # g/L
        "creatinine": 88.4,      # µmol/L
        "glucose": 5.0,          # mmol/L
        "crp": 0.1,              # mg/dL
        "lymphocyte_pct": 30.0,  # %
        "mcv": 90.0,             # fL
        "rdw": 12.5,             # %
        "alp": 70.0,             # U/L
        "wbc": 6.0,              # 10^9/L
    }
    chronological_age = 50.0

    result = calculate_phenoage(biomarkers, chronological_age)

    assert result["is_valid"] is True
    assert result["phenoage"] is not None
    # Biological age should be roughly 40.9 +/- 0.5 years
    assert 40.0 <= result["phenoage"] <= 42.0
    assert result["age_acceleration"] is not None
    # Age acceleration should be negative (biologically younger)
    assert result["age_acceleration"] < 0
    assert len(result["missing_markers"]) == 0


def test_phenoage_missing_crp_returns_null():
    from app.core.phenoage import calculate_phenoage

    # Missing CRP
    biomarkers = {
        "albumin": 45.0,
        "creatinine": 88.4,
        "glucose": 5.0,
        # "crp": None - MISSING
        "lymphocyte_pct": 30.0,
        "mcv": 90.0,
        "rdw": 12.5,
        "alp": 70.0,
        "wbc": 6.0,
    }
    chronological_age = 50.0

    result = calculate_phenoage(biomarkers, chronological_age)

    assert result["is_valid"] is False
    assert result["phenoage"] is None
    assert result["age_acceleration"] is None
    assert "crp" in result["missing_markers"]


def test_risk_flags_evaluation():
    from app.core.phenoage import evaluate_risk_flags

    # Patient with pre-diabetes and elevated triglycerides
    biomarkers = {
        "glucose_fasting": 115.0,  # mg/dL (Pre-diabetes range)
        "hba1c": 6.1,             # % (Pre-diabetes range)
        "triglycerides": 210.0,    # mg/dL (High)
        "cholesterol_total": 220.0,# mg/dL (Borderline)
        "creatinine": 0.9,
    }
    flags = evaluate_risk_flags(biomarkers, sex="male")

    glycemic = next((f for f in flags if f["category"] == "glycemic"), None)
    lipid = next((f for f in flags if f["category"] == "cardiovascular_lipid"), None)

    assert glycemic is not None
    assert glycemic["status"] == "elevated"
    assert "pre-diabetes" in glycemic["message"].lower()

    assert lipid is not None
    assert lipid["status"] == "elevated"
    assert "triglyceride" in lipid["message"].lower()
