import io
import pytest
from fastapi.testclient import TestClient


def test_api_health_endpoint():
    from app.main import app
    client = TestClient(app)
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_api_sample_reports_list():
    from app.main import app
    client = TestClient(app)
    response = client.get("/api/sample-reports")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_api_extract_file():
    from app.main import app
    client = TestClient(app)
    
    # Create a small simulated text file with blood report content
    report_content = b"""
    Dr Lal PathLabs
    Patient Name: Anita Sharma   Age: 38   Gender: Female
    Date: 2026-11-18
    
    Test Description         Result   Units    Reference
    Serum Albumin            4.5      g/dL     3.5 - 5.0
    Fasting Blood Glucose    92       mg/dL    70 - 99
    Serum Creatinine         0.8      mg/dL    0.6 - 1.2
    """
    files = {"file": ("report.txt", io.BytesIO(report_content), "text/plain")}
    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert "patient_info" in res_json
    assert "biomarkers" in res_json
    assert "extraction_metadata" in res_json
    assert len(res_json["biomarkers"]) >= 2
