import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.llm.chat import (
    ChatBiomarker,
    ChatMessage,
    ChatRequest,
    _build_report_context,
    answer_health_question,
)
from app.main import app


def test_chat_request_rejects_blank_message():
    with pytest.raises(ValidationError):
        ChatRequest(message="   ")


def test_report_context_includes_only_confirmed_biomarkers():
    req = ChatRequest(
        message="Explain my results",
        biomarkers=[
            ChatBiomarker(
                display_name="Hemoglobin",
                value=13.2,
                unit="g/dL",
                reference_range="12.0-15.5",
                confirmed=True,
            ),
            ChatBiomarker(
                display_name="Unconfirmed glucose",
                value=999,
                unit="mg/dL",
                confirmed=False,
            ),
        ],
        chronological_age=28,
    )

    context = _build_report_context(req)
    assert "Hemoglobin: 13.2 g/dL" in context
    assert "Unconfirmed glucose" not in context
    assert "Chronological age supplied by user: 28" in context
    assert "PhenoAge: unavailable" in context


def test_chat_history_is_bounded():
    with pytest.raises(ValidationError):
        ChatRequest(
            message="Hello",
            history=[{"role": "user", "content": "x"} for _ in range(13)],
        )


def test_chat_endpoint_requires_consent_403(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")
    client = TestClient(app)

    with patch("app.llm.chat.httpx.Client") as mock_http:
        # Default allow_cloud_llm=False
        resp = client.post("/api/chat", json={"message": "What does my glucose mean?"})
        assert resp.status_code == 403
        assert "consent" in resp.json()["detail"].lower()
        assert mock_http.call_count == 0


def test_chat_redacts_pii_before_openrouter_call(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-test-key")

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Your fasting glucose is mildly elevated."}}]
    }
    mock_response.raise_for_status.return_value = None

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_response
    mock_client_cm = MagicMock()
    mock_client_cm.__enter__.return_value = mock_client_instance
    mock_client_cm.__exit__.return_value = False

    req = ChatRequest(
        message="My email is rohit.kumar@example.com and phone +91 9876543210. Explain glucose 118.",
        history=[
            ChatMessage(
                role="user",
                content="Patient Name: Rohit Kumar, Aadhaar: 1234 5678 9012, DOB: 1980-01-10",
            )
        ],
        biomarkers=[
            ChatBiomarker(
                display_name="Fasting Glucose",
                value=118.0,
                unit="mg/dL",
                reference_range="70 - 99",
                flag="high",
                confirmed=True,
            )
        ],
        chronological_age=46,
        allow_cloud_llm=True,
    )

    with patch("app.llm.chat.httpx.Client", return_value=mock_client_cm):
        res = answer_health_question(req)

    assert "elevated" in res.reply
    sent_payload = mock_client_instance.post.call_args.kwargs["json"]
    serialized_messages = str(sent_payload["messages"])
    assert "rohit.kumar@example.com" not in serialized_messages
    assert "9876543210" not in serialized_messages
    assert "Rohit Kumar" not in serialized_messages
    assert "1234 5678 9012" not in serialized_messages
    assert "1980-01-10" not in serialized_messages
    assert "118.0" in serialized_messages
