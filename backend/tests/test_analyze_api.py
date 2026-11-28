import pytest
from fastapi.testclient import TestClient


def test_analyze_endpoint_full_report():
    from app.main import app
    client = TestClient(app)

    payload = {
        "chronological_age": 45.0,
        "patient_gender": "male",
        "biomarkers": [
            {"standard_id": "albumin", "display_name": "Albumin", "raw_name": "Albumin", "value": 4.5, "unit": "g/dL", "standard_unit": "g/dL"},
            {"standard_id": "creatinine", "display_name": "Creatinine", "raw_name": "Creatinine", "value": 0.9, "unit": "mg/dL", "standard_unit": "mg/dL"},
            {"standard_id": "glucose_fasting", "display_name": "Glucose", "raw_name": "Glucose", "value": 88.0, "unit": "mg/dL", "standard_unit": "mg/dL"},
            {"standard_id": "crp", "display_name": "CRP", "raw_name": "hs-CRP", "value": 0.8, "unit": "mg/L", "standard_unit": "mg/L"},
            {"standard_id": "lymphocyte_pct", "display_name": "Lymphocytes", "raw_name": "Lymphocytes", "value": 32.0, "unit": "%", "standard_unit": "%"},
            {"standard_id": "mcv", "display_name": "MCV", "raw_name": "MCV", "value": 89.0, "unit": "fL", "standard_unit": "fL"},
            {"standard_id": "rdw", "display_name": "RDW", "raw_name": "RDW", "value": 12.8, "unit": "%", "standard_unit": "%"},
            {"standard_id": "alp", "display_name": "ALP", "raw_name": "ALP", "value": 78.0, "unit": "U/L", "standard_unit": "U/L"},
            {"standard_id": "wbc", "display_name": "WBC", "raw_name": "WBC", "value": 6800.0, "unit": "cells/cumm", "standard_unit": "10^9/L"},
            {"standard_id": "cholesterol_total", "display_name": "Cholesterol", "raw_name": "Cholesterol", "value": 180.0, "unit": "mg/dL", "standard_unit": "mg/dL"},
        ]
    }

    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["chronological_age"] == 45.0
    assert data["phenoage"]["is_valid"] is True
    assert data["phenoage"]["phenoage"] is not None
    assert len(data["risk_flags"]) >= 1
    assert "US population" in data["population_caveat"]


def test_analyze_endpoint_missing_crp():
    from app.main import app
    client = TestClient(app)

    payload = {
        "chronological_age": 52.0,
        "patient_gender": "female",
        "biomarkers": [
            {"standard_id": "albumin", "display_name": "Albumin", "raw_name": "Albumin", "value": 4.1, "unit": "g/dL", "standard_unit": "g/dL"},
            {"standard_id": "glucose_fasting", "display_name": "Glucose", "raw_name": "Glucose", "value": 115.0, "unit": "mg/dL", "standard_unit": "mg/dL"},
            # CRP is missing
        ]
    }

    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["phenoage"]["is_valid"] is False
    assert data["phenoage"]["phenoage"] is None
    assert "crp" in data["phenoage"]["missing_markers"]
    # Risk flags still compute even without CRP
    glycemic = next((f for f in data["risk_flags"] if f["category"] == "glycemic"), None)
    assert glycemic is not None
    assert glycemic["status"] == "elevated"


def test_analyze_rejects_unconfirmed_values_from_phenoage():
    from app.main import app
    client = TestClient(app)

    payload = {
        "chronological_age": 45.0,
        "patient_gender": "male",
        "biomarkers": [
            {"standard_id": "albumin", "display_name": "Albumin", "raw_name": "Albumin", "value": 4.5, "unit": "g/dL", "standard_unit": "g/dL"},
            {"standard_id": "creatinine", "display_name": "Creatinine", "raw_name": "Creatinine", "value": 0.9, "unit": "mg/dL", "standard_unit": "mg/dL"},
            {"standard_id": "glucose_fasting", "display_name": "Glucose", "raw_name": "Glucose", "value": 88.0, "unit": "mg/dL", "standard_unit": "mg/dL"},
            {"standard_id": "crp", "display_name": "CRP", "raw_name": "hs-CRP", "value": 0.8, "unit": "mg/L", "standard_unit": "mg/L", "confidence": 0.6, "needs_review": True},
            {"standard_id": "lymphocyte_pct", "display_name": "Lymphocytes", "raw_name": "Lymphocytes", "value": 32.0, "unit": "%", "standard_unit": "%"},
            {"standard_id": "mcv", "display_name": "MCV", "raw_name": "MCV", "value": 89.0, "unit": "fL", "standard_unit": "fL"},
            {"standard_id": "rdw", "display_name": "RDW", "raw_name": "RDW", "value": 12.8, "unit": "%", "standard_unit": "%"},
            {"standard_id": "alp", "display_name": "ALP", "raw_name": "ALP", "value": 78.0, "unit": "U/L", "standard_unit": "U/L"},
            {"standard_id": "wbc", "display_name": "WBC", "raw_name": "WBC", "value": 6.8, "unit": "10^3/uL", "standard_unit": "10^9/L"},
        ],
    }

    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["phenoage"]["is_valid"] is False
    assert data["phenoage"]["phenoage"] is None
    assert "crp" in data["phenoage"]["missing_markers"]
