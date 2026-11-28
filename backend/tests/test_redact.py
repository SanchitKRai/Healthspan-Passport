import json
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.llm.chat import ChatRequest, answer_health_question
from app.llm.client import extract_biomarkers_with_llm
from app.llm.redact import minimize_to_result_lines, redact_pii
from app.main import app


def _mock_httpx_success(reply_content: str):
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": reply_content}}]
    }
    mock_response.raise_for_status.return_value = None

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = mock_client_instance
    mock_cm.__exit__.return_value = False
    return mock_cm, mock_client_instance


RED_TEAM_REPORTS = [
    (
        "unlabelled_header_honorific",
        "Mr. Aarav Sharma\nFasting Blood Glucose: 108 mg/dL\nSerum Albumin: 4.4 g/dL",
        ["Aarav Sharma"],
        ["108", "4.4"],
    ),
    (
        "guardian_so_do_lines",
        "S/O Rajesh Verma\nD/O Sunita Nair\nSerum Creatinine: 0.9 mg/dL\nMCV: 88.5 fL",
        ["Rajesh Verma", "Sunita Nair"],
        ["0.9", "88.5"],
    ),
    (
        "pathologist_signature_dr",
        "RDW-CV: 13.4 %\nAlkaline Phosphatase: 86 U/L\nChecked by: Dr. Kavita Deshmukh, MD (Pathology)\nDr. Arvind Kulkarni",
        ["Kavita Deshmukh", "Arvind Kulkarni"],
        ["13.4", "86"],
    ),
    (
        "unlabelled_address_with_pincode",
        "Flat 4B, Shanti Enclave, 42 MG Road, Indiranagar, Bengaluru 560038\nTotal Cholesterol: 192 mg/dL",
        ["Shanti Enclave", "42 MG Road", "560038", "Bengaluru"],
        ["192"],
    ),
    (
        "barcodes_and_accession_numbers",
        "Barcode: BC-88472910\nAccession # ACC908172\n*SP991044*\nWBC Count: 6.8 10^3/uL",
        ["BC-88472910", "ACC908172", "SP991044"],
        ["6.8"],
    ),
    (
        "footer_phone_and_landline",
        "hs-CRP: 1.8 mg/L\nLymphocytes: 31 %\n24x7 Lab Helpline: 022-24123456\nFooter call +91 9820012345",
        ["022-24123456", "9820012345"],
        ["1.8", "31"],
    ),
    (
        "adjacent_header_and_split_table_row",
        "Mrs. Meena Krishnan\nS/O Late Venkat Krishnan\nSerum Albumin\n4.3 g/dL\n14 Park Street, Kolkata 700016",
        ["Meena Krishnan", "Venkat Krishnan", "Park Street", "700016"],
        ["4.3", "Albumin"],
    ),
    (
        "demographics_never_sent_as_text",
        "Patient Name:Vikram Sethi\nAge: 47   Gender: Male   Report Date: 2026-11-18\nTriglycerides: 145 mg/dL",
        ["Vikram Sethi", "2026-11-18", "Age: 47", "Gender: Male"],
        ["145"],
    ),
    (
        "hindi_name_and_pan_aadhaar",
        "Smt. Kamla Devi\nPAN: ABCDE1234F\nAadhaar 4321-8765-9988\nHbA1c: 5.9 %",
        ["Kamla Devi", "ABCDE1234F", "4321-8765-9988"],
        ["5.9"],
    ),
    (
        "mixed_clinical_and_footer_signature",
        "Order ID: ORD-77123\nSerum Albumin: 4.1 g/dL\nVerified by Dr. N. Subramanian\nHouse No. 88, Lajpat Nagar, New Delhi 110024",
        ["ORD-77123", "Subramanian", "Lajpat Nagar", "110024"],
        ["4.1"],
    ),
]


@pytest.mark.parametrize("case_id,raw_report,forbidden_strings,expected_kept", RED_TEAM_REPORTS)
def test_red_team_extraction_strips_awkward_pii(case_id, raw_report, forbidden_strings, expected_kept):
    mock_payload = json.dumps({
        "patient_info": {},
        "biomarkers": [{"standard_id": "glucose_fasting", "value": 100.0, "unit": "mg/dL"}],
    })
    mock_cm, mock_client = _mock_httpx_success(mock_payload)

    with patch("app.llm.client.httpx.Client", return_value=mock_cm):
        extract_biomarkers_with_llm(raw_report, api_key="sk-test-key", allow_cloud_llm=True)

    assert mock_client.post.call_count == 1
    sent_json = mock_client.post.call_args.kwargs["json"]
    assert sent_json["provider"] == {"data_collection": "deny"}
    outbound_text = json.dumps(sent_json["messages"])

    for secret in forbidden_strings:
        assert secret not in outbound_text, f"{case_id}: leaked {secret!r} in outbound payload"
    for biomarker_token in expected_kept:
        assert biomarker_token in outbound_text, f"{case_id}: lost {biomarker_token!r}"


def test_red_team_structured_age_gender_date_preserved_locally():
    raw_report = (
        "Patient Name: Mr. Aarav Sharma\n"
        "Age: 47  Gender: Male  Report Date: 2026-11-18\n"
        "Lab: Apollo Diagnostics\n"
        "Fasting Glucose: 102 mg/dL\n"
    )
    mock_payload = json.dumps({
        "patient_info": {"name": None, "age": None, "gender": None, "report_date": None, "lab_name": None},
        "biomarkers": [{"standard_id": "glucose_fasting", "value": 102.0, "unit": "mg/dL"}],
    })
    mock_cm, mock_client = _mock_httpx_success(mock_payload)

    with patch("app.llm.client.httpx.Client", return_value=mock_cm):
        res = extract_biomarkers_with_llm(raw_report, api_key="sk-test-key", allow_cloud_llm=True)

    outbound_text = json.dumps(mock_client.post.call_args.kwargs["json"]["messages"])
    assert "Aarav Sharma" not in outbound_text
    assert "47" not in outbound_text
    assert "Male" not in outbound_text
    assert "2026-11-18" not in outbound_text
    assert res.patient_info.age == 47.0
    assert res.patient_info.gender == "male"
    assert res.patient_info.report_date == "2026-11-18"


def test_minimize_to_result_lines_zero_lines_skips_cloud_call():
    no_biomarkers_text = (
        "Mr. Aarav Sharma\n"
        "42 MG Road, Indiranagar, Bengaluru 560038\n"
        "Barcode: BC-88472910\n"
        "Phone: +91 9811122233\n"
    )
    minimized, stats = minimize_to_result_lines(no_biomarkers_text)
    assert minimized == ""
    assert stats["kept_lines"] == 0

    with patch("app.llm.client.httpx.Client") as mock_http:
        res = extract_biomarkers_with_llm(no_biomarkers_text, api_key="sk-test-key", allow_cloud_llm=True)
        assert mock_http.call_count == 0
        assert "minimized-zero-lines-local-fallback" in res.extraction_metadata.model_used


def test_red_team_chat_self_intro_redaction_and_provider_setting(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    mock_cm, mock_client = _mock_httpx_success("HbA1c reflects your 3-month average blood sugar.")

    req = ChatRequest(
        message="Hi, my name is Ravi and this is Kavita Nair. I am worried about HbA1c 6.4% and 9811122233.",
        history=[],
        allow_cloud_llm=True,
    )
    with patch("app.llm.chat.httpx.Client", return_value=mock_cm):
        res = answer_health_question(req)

    assert "HbA1c" in res.reply
    sent_json = mock_client.post.call_args.kwargs["json"]
    assert sent_json["provider"] == {"data_collection": "deny"}
    outbound_text = json.dumps(sent_json["messages"])
    assert "Ravi" not in outbound_text
    assert "Kavita Nair" not in outbound_text
    assert "9811122233" not in outbound_text
    # Non-name clinical adjectives after "I am" must remain intact
    assert "worried" in outbound_text
    assert "6.4%" in outbound_text


def test_fail_closed_if_redaction_fails_no_outbound_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    with patch("app.llm.client.redact_pii", side_effect=RuntimeError("Redaction engine failure")), patch(
        "app.llm.client.httpx.Client"
    ) as mock_http:
        with pytest.raises(RuntimeError, match="Redaction engine failure"):
            extract_biomarkers_with_llm("Fasting Glucose: 102 mg/dL", api_key="sk-test-key", allow_cloud_llm=True)
        assert mock_http.call_count == 0

    with patch("app.llm.chat.redact_pii", side_effect=RuntimeError("Redaction engine failure")), patch(
        "app.llm.chat.httpx.Client"
    ) as mock_http:
        with pytest.raises(RuntimeError, match="Redaction engine failure"):
            answer_health_question(ChatRequest(message="Explain HbA1c", allow_cloud_llm=True))
        assert mock_http.call_count == 0


def test_chat_missing_key_returns_503_and_no_consent_returns_403(monkeypatch):
    client = TestClient(app)

    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    resp_403 = client.post("/api/chat", json={"message": "Explain glucose"})
    assert resp_403.status_code == 403

    resp_503 = client.post("/api/chat", json={"message": "Explain glucose", "allow_cloud_llm": True})
    assert resp_503.status_code == 503


def test_extract_endpoint_closes_uploaded_file_handle():
    import io
    from fastapi import UploadFile
    from app.main import extract_report

    upload = UploadFile(filename="Mr_Aarav_Sharma_report.txt", file=io.BytesIO(b"Serum Albumin: 4.5 g/dL\n"))
    resp = extract_report(file=upload, allow_cloud_llm=False)
    assert resp.extraction_metadata.total_biomarkers_found >= 1
    assert upload.file.closed is True


@pytest.mark.parametrize(
    "result_line,expected_tokens",
    [
        ("Platelet Count 250000 /cumm", ["Platelet Count", "250000", "/cumm"]),
        ("Total WBC 7200 /cumm", ["Total WBC", "7200", "/cumm"]),
        ("RBC 4.8 million/cumm", ["RBC", "4.8", "million/cumm"]),
        ("HbA1c: 5.9 %", ["HbA1c", "5.9", "%"]),
        ("Lymphocyte Absolute Count 210000 cells/cumm", ["210000", "cells/cumm"]),
        ("Platelets: 415000", ["Platelets", "415000"]),
    ],
)
def test_real_lab_values_including_6_digit_counts_survive_redaction(result_line, expected_tokens):
    minimized, stats = minimize_to_result_lines(result_line)
    assert stats["kept_lines"] == 1
    redacted, counts = redact_pii(minimized)
    assert "[REDACTED_" not in redacted, f"Unexpected redaction in {result_line!r}: {redacted!r} ({counts})"
    for tok in expected_tokens:
        assert tok in redacted, f"Token {tok!r} lost from {result_line!r} -> {redacted!r}"


def test_pincodes_still_redacted_with_address_context():
    line = "42 MG Road, Indiranagar, Bengaluru 560038"
    redacted, _ = redact_pii(line)
    assert "560038" not in redacted
    assert "[REDACTED_ADDRESS]" in redacted

    minimized, _ = minimize_to_result_lines(line)
    assert "560038" not in minimized


def test_all_15_sample_reports_preserve_extracted_biomarker_values():
    from pathlib import Path
    from app.extraction.extractor import extract_text_from_file

    repo_root = Path(__file__).resolve().parent.parent.parent
    gt = json.loads((repo_root / "data" / "ground_truth.json").read_text(encoding="utf-8"))
    sample_dir = repo_root / "data" / "sample_reports"

    for fname, info in sorted(gt.items()):
        raw_text, _ = extract_text_from_file((sample_dir / fname).read_bytes(), fname)
        minimized, _ = minimize_to_result_lines(raw_text)
        redacted, _ = redact_pii(minimized)

        for key, meta in info.get("biomarkers", {}).items():
            val = meta["value"]
            val_int = str(int(val)) if float(val).is_integer() else str(val)
            val_str = str(val)
            present_in_raw = (val_str in raw_text) or (val_int in raw_text)
            if present_in_raw:
                assert (val_str in redacted) or (val_int in redacted), (
                    f"{fname}: ground-truth {key}={val} was present in extracted text "
                    f"but lost/altered by minimize+redact"
                )
