import pytest


def test_unit_normalization_conversions():
    from app.core.normalizer import normalize_biomarker

    # 1. Albumin: 4.2 g/dL -> 42.0 g/L
    val, unit, ref = normalize_biomarker("albumin", 4.2, "g/dL")
    assert round(val, 2) == 42.0
    assert unit == "g/L"

    # 2. Creatinine: 1.0 mg/dL -> 88.4 µmol/L
    val, unit, ref = normalize_biomarker("creatinine", 1.0, "mg/dL")
    assert round(val, 2) == 88.4
    assert unit == "µmol/L"

    # 3. Glucose: 90.0 mg/dL -> ~4.99 mmol/L
    val, unit, ref = normalize_biomarker("glucose_fasting", 90.0, "mg/dL")
    assert round(val, 2) == 4.99
    assert unit == "mmol/L"

    # 4. CRP: 2.0 mg/L -> 0.2 mg/dL
    val, unit, ref = normalize_biomarker("crp", 2.0, "mg/L")
    assert round(val, 3) == 0.2
    assert unit == "mg/dL"

    # 5. WBC: 6500 cells/cumm -> 6.5 10^9/L
    val, unit, ref = normalize_biomarker("wbc", 6500.0, "cells/cumm")
    assert round(val, 2) == 6.5
    assert unit == "10^9/L"

    # 6. Already normalized units stay unchanged
    val, unit, ref = normalize_biomarker("albumin", 45.0, "g/L")
    assert val == 45.0
    assert unit == "g/L"


def test_indian_reference_ranges():
    from app.core.normalizer import get_reference_range

    # Fasting glucose (mg/dL) Indian reference
    ref_glucose = get_reference_range("glucose_fasting", "mg/dL")
    assert ref_glucose["low"] == 70.0
    assert ref_glucose["high"] == 99.0

    # Hemoglobin sex-specific reference
    ref_hb_male = get_reference_range("hemoglobin", "g/dL", sex="male")
    ref_hb_female = get_reference_range("hemoglobin", "g/dL", sex="female")
    assert ref_hb_male["low"] == 13.0
    assert ref_hb_female["low"] == 12.0
