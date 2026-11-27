"""
Deterministic PII Redaction before outbound Cloud LLM calls.

Strips names, phone numbers, emails, government/hospital IDs, dates/DOBs,
and street/pincode addresses while preserving numeric biomarker values,
units, chronological ages, and clinical reference ranges.
"""

import re
from typing import Dict, Tuple


_PATTERNS = [
    # Email addresses
    (
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "[REDACTED_EMAIL]",
    ),
    # PAN (India: 5 uppercase letters, 4 digits, 1 uppercase letter)
    (
        "id",
        re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
        "[REDACTED_ID]",
    ),
    # Aadhaar (labeled or 4-4-4 grouped 12 digits)
    (
        "id",
        re.compile(r"(?i)\b(aadhaar|aadhar|uidai)\s*[:|#-]?\s*[\d\s-]{10,16}"),
        r"\1: [REDACTED_ID]",
    ),
    (
        "id",
        re.compile(r"\b\d{4}[\s-]\d{4}[\s-]\d{4}\b"),
        "[REDACTED_ID]",
    ),
    # Labeled Patient / Hospital / Lab / SSN identifiers
    (
        "id",
        re.compile(
            r"(?i)\b(uhid|mrn|patient\s*id|pt\.?\s*id|reg(?:istration)?\s*(?:no|id|#)|"
            r"lab\s*(?:no|id)|sample\s*id|accession\s*(?:no|id)?|passport\s*(?:no|id)?|ssn)"
            r"\s*[:|#-]?\s*[A-Z0-9][A-Z0-9/_-]{2,24}"
        ),
        r"\1: [REDACTED_ID]",
    ),
    # Labeled DOB / Birth Date / Collection Date
    (
        "date",
        re.compile(
            r"(?i)\b(dob|date\s+of\s+birth|birth\s*date|report\s*date|collected(?:\s+on)?|date)"
            r"\s*[:|]?\s*(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}|\d{1,2}[-/\s][A-Za-z]{3,9}[-/,\s]+\d{2,4})"
        ),
        r"\1: [REDACTED_DATE]",
    ),
    # Standalone calendar dates (YYYY-MM-DD, DD/MM/YYYY, DD-MMM-YYYY)
    (
        "date",
        re.compile(
            r"\b(?:\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{1,2}[-/\s](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-/,\s]+\d{2,4})\b",
            re.IGNORECASE,
        ),
        "[REDACTED_DATE]",
    ),
    # Labeled phone numbers
    (
        "phone",
        re.compile(r"(?i)\b(phone|ph|mob|mobile|tel|contact(?:\s+no)?)\s*[:|]?\s*(?:\+?\d[\d\s().-]{6,16}\d)"),
        r"\1: [REDACTED_PHONE]",
    ),
    # Indian +91 / 10-digit mobile numbers (starting 6-9) and formatted 10-digit numbers
    (
        "phone",
        re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"),
        "[REDACTED_PHONE]",
    ),
    (
        "phone",
        re.compile(r"\b\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    # Labeled patient names (avoid matching Test Name / Lab Name / Assay Name)
    (
        "name",
        re.compile(
            r"(?i)\b((?:patient\s+name|pt\.?\s*name|patient|(?<!test\s)(?<!lab\s)(?<!assay\s)(?<!parameter\s)name)"
            r"\s*[:|]\s*)([A-Za-z][A-Za-z.\s'-]{1,45}?)(?=\s*(?:\r?\n|,|\||age\b|gender\b|sex\b|dob\b|date\b|$))"
        ),
        r"\1[REDACTED_NAME]",
    ),
    # Labeled referring physician / doctor names
    (
        "name",
        re.compile(
            r"(?i)\b((?:ref(?:erred)?\s*by|consultant|ordering\s+physician|doctor)\s*[:|]\s*)"
            r"((?:Dr\.?\s+)?[A-Za-z][A-Za-z.\s'-]{1,45}?)(?=\s*(?:\r?\n|,|\||$))"
        ),
        r"\1[REDACTED_DOCTOR]",
    ),
    # Labeled street / home addresses
    (
        "address",
        re.compile(r"(?i)\b(address|addr|residence)\s*[:|]\s*[^\r\n]{4,140}"),
        r"\1: [REDACTED_ADDRESS]",
    ),
]


def redact_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """
    Redact personally identifiable information from clinical text before outbound LLM calls.
    Returns (redacted_text, counts_by_category).
    """
    if not text:
        return text, {}

    redacted = text
    counts: Dict[str, int] = {}

    for category, pattern, replacement in _PATTERNS:
        redacted, n = pattern.subn(replacement, redacted)
        if n > 0:
            counts[category] = counts.get(category, 0) + n

    return redacted, counts
