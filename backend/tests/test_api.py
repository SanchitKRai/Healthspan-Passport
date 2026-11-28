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


def test_api_extract_consent_gating(monkeypatch):
    from unittest.mock import patch
    from app.main import app

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    client = TestClient(app)

    report_content = b"Patient Name: Anita Sharma\nFasting Blood Glucose: 92 mg/dL\n"

    # Default (no allow_cloud_llm) must NOT invoke OpenRouter
    with patch("app.llm.client.call_openrouter_api") as mock_api:
        files = {"file": ("report.txt", io.BytesIO(report_content), "text/plain")}
        resp = client.post("/api/extract", files=files)
        assert resp.status_code == 200
        assert mock_api.call_count == 0
        assert "local-only" in resp.json()["extraction_metadata"]["model_used"]

    # Explicit opt-in allow_cloud_llm=true passes redacted text to OpenRouter
    with patch("app.llm.client.call_openrouter_api") as mock_api:
        mock_api.return_value = '{"patient_info": {}, "biomarkers": [{"standard_id": "glucose_fasting", "value": 92.0, "unit": "mg/dL"}]}'
        files = {"file": ("report.txt", io.BytesIO(report_content), "text/plain")}
        resp = client.post("/api/extract", files=files, data={"allow_cloud_llm": "true"})
        assert resp.status_code == 200
        assert mock_api.call_count == 1
        sent_prompt = mock_api.call_args[0][1]
        assert "Anita Sharma" not in sent_prompt
        assert "92" in sent_prompt


def test_api_sample_extract_consent_gating(monkeypatch):
    from unittest.mock import patch
    from app.main import app

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    client = TestClient(app)

    with patch("app.llm.client.call_openrouter_api") as mock_api:
        resp = client.post("/api/extract-sample/01_dr_lal_healthy_adult.pdf")
        assert resp.status_code == 200
        assert mock_api.call_count == 0
        assert "local-only" in resp.json()["extraction_metadata"]["model_used"]


def test_extract_preview_endpoints_strip_pii_without_cloud_call():
    from unittest.mock import patch
    from app.main import app

    client = TestClient(app)
    report_content = b"Mr. Aarav Sharma\n42 MG Road, Bengaluru 560038\nFasting Blood Glucose: 98 mg/dL\n"

    with patch("app.llm.client.call_openrouter_api") as mock_api:
        files = {"file": ("report.txt", io.BytesIO(report_content), "text/plain")}
        resp = client.post("/api/extract/preview", files=files)
        assert resp.status_code == 200
        assert mock_api.call_count == 0
        data = resp.json()
        assert data["zero_lines"] is False
        assert "Aarav Sharma" not in data["outbound_text"]
        assert "560038" not in data["outbound_text"]
        assert "98 mg/dL" in data["outbound_text"]

        sample_resp = client.post("/api/extract-sample/01_dr_lal_healthy_adult.pdf/preview")
        assert sample_resp.status_code == 200
        assert mock_api.call_count == 0
        assert sample_resp.json()["zero_lines"] is False


def test_cors_settings_defaults_and_env_parsing(monkeypatch):
    from app.main import DEFAULT_LOCALHOST_ORIGINS, get_cors_settings

    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.delenv("ALLOW_ORIGIN_REGEX", raising=False)
    default_cfg = get_cors_settings()
    assert default_cfg["allow_origins"] == DEFAULT_LOCALHOST_ORIGINS
    assert "*" not in default_cfg["allow_origins"]
    assert default_cfg["allow_origin_regex"] is None

    monkeypatch.setenv("CORS_ORIGINS", "https://healthspan-passport.vercel.app/, *, http://localhost:3000")
    monkeypatch.setenv("ALLOW_ORIGIN_REGEX", r"^https://healthspan-passport(?:-[a-z0-9-]+)?\.vercel\.app$")
    prod_cfg = get_cors_settings()
    assert prod_cfg["allow_origins"] == ["https://healthspan-passport.vercel.app", "http://localhost:3000"]
    assert prod_cfg["allow_origin_regex"] == r"^https://healthspan-passport(?:-[a-z0-9-]+)?\.vercel\.app$"

