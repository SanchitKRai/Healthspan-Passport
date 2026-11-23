import pytest
from pydantic import ValidationError

from app.llm.chat import ChatBiomarker, ChatRequest, _build_report_context


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
