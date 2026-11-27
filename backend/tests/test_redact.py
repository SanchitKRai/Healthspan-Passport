from app.llm.redact import redact_pii


def test_redact_pii_strips_identifiers_and_preserves_clinical_values():
    raw_report = """
    Metropolis Healthcare
    Patient Name: Aarav Sharma   Age: 47   Gender: Male
    DOB: 1979-04-15   Report Date: 2026-11-12
    Referred By: Dr. R. Mehta
    Mobile: +91 9876543210   Email: aarav.sharma@example.com
    UHID: MH-998812   Aadhaar: 1234 5678 9012   PAN: ABCDE1234F
    Address: 42 MG Road, Bengaluru 560001

    Test Name: Fasting Blood Glucose   Result: 118.0   Unit: mg/dL   Ref: 70 - 99
    Serum Albumin                      4.2             g/dL            3.5 - 5.0
    Platelet Count                     250000          /uL             150000 - 450000
    """

    redacted, counts = redact_pii(raw_report)

    # PII must be removed
    assert "Aarav Sharma" not in redacted
    assert "Dr. R. Mehta" not in redacted
    assert "9876543210" not in redacted
    assert "aarav.sharma@example.com" not in redacted
    assert "1979-04-15" not in redacted
    assert "2026-11-12" not in redacted
    assert "MH-998812" not in redacted
    assert "1234 5678 9012" not in redacted
    assert "ABCDE1234F" not in redacted
    assert "42 MG Road" not in redacted

    # Clinical values, test names, age, and reference ranges must remain intact
    assert "Test Name: Fasting Blood Glucose" in redacted
    assert "118.0" in redacted
    assert "4.2" in redacted
    assert "250000" in redacted
    assert "70 - 99" in redacted
    assert "Age: 47" in redacted
    assert counts.get("name", 0) >= 1
    assert counts.get("phone", 0) >= 1
    assert counts.get("email", 0) == 1
    assert counts.get("id", 0) >= 3
