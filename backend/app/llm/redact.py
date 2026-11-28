"""
Deterministic PII Redaction and Minimization before outbound Cloud LLM calls.

Minimization keeps only biomarker/measurement lines (+-1 split-row context
when safe) and drops headers, footers, signatures, addresses, barcodes, and
patient demographics. Redaction strips names, relational lines (S/O, D/O),
doctor signatures, phone numbers, emails, IDs/barcodes, dates/DOBs,
street/pincode addresses, and self-introduced chat names.
"""

import re
from typing import Any, Dict, List, Tuple

from app.core.normalizer import BIOMARKER_ALIASES


def _build_biomarker_alias_regex() -> re.Pattern:
    aliases: List[str] = []
    for terms in BIOMARKER_ALIASES.values():
        aliases.extend(terms)
    # Longest first so multi-word names match before short acronyms
    aliases = sorted(set(aliases), key=len, reverse=True)
    escaped = [re.escape(term).replace(r"\ ", r"\s+") for term in aliases]
    return re.compile(r"(?i)(?<![A-Za-z0-9])(?:" + "|".join(escaped) + r")(?![A-Za-z0-9])")


_BIOMARKER_ALIAS_REGEX = _build_biomarker_alias_regex()

_NUMBER_UNIT_REGEX = re.compile(
    r"(?i)(?<![A-Za-z0-9/])\d+(?:\.\d+)?\s*(?:"
    r"mg/dl|g/dl|g/l|mmol/l|umol/l|µmol/l|μmol/l|mg/l|iu/l|u/l|fl|pg|"
    r"meq/l|ng/ml|pg/ml|ng/dl|ug/dl|µg/dl|mm/hr|"
    r"x?\s*10\^[369]/[uµμ]?l|cells/cumm|lakhs?/cumm|k/[uµμ]l|m/[uµμ]l|%"
    r")(?![A-Za-z])"
)

# Lines matching clear non-result metadata should never be pulled into +-1 context expansion.
_NON_RESULT_CONTEXT_LINE = re.compile(
    r"(?i)(?:"
    r"\b(?:patient\s*name|pt\.?\s*name|patient\s*id|pt\.?\s*id|uhid|mrn|"
    r"accession|barcode|bar\s*code|specimen|sample\s*id|order\s*id|"
    r"dob|date\s+of\s+birth|birth\s*date|report\s*date|collected|"
    r"age\s*[:|/]|sex\s*[:|/]|gender\s*[:|/]|"
    r"address|residence|pincode|pin\s*code|phone|mobile|tel|helpline|fax|email|"
    r"ref(?:erred)?\s*by|pathologist|verified\s*by|signed\s*by|signature|"
    r"lab\s*director|consultant)\b|"
    r"^\s*(?:mr|mrs|ms|miss|smt|shri|dr)\.?\s+[A-Za-z]|"
    r"\b(?:s/o|d/o|w/o|c/o)\b|"
    r"@|"
    r"\b[1-8]\d{5}\b"
    r")"
)

_CHAT_NON_NAME_WORDS = {
    "a", "an", "about", "after", "all", "already", "also", "always", "anxious",
    "asking", "aware", "bad", "concerned", "confused", "curious", "diabetic",
    "doing", "done", "eating", "fasting", "feeling", "female", "fine", "getting",
    "going", "good", "having", "healthy", "here", "high", "hungry", "just",
    "looking", "low", "male", "new", "normal", "not", "ok", "okay", "old",
    "pre", "prediabetic", "pregnant", "reading", "seeing", "sending", "sharing",
    "sick", "still", "sure", "taking", "testing", "the", "tired", "trying",
    "unsure", "uploading", "vegan", "vegetarian", "very", "waiting", "wondering",
    "worried", "years", "yrs",
}


def _redact_chat_self_intro(match: re.Match) -> str:
    prefix = match.group(1)
    candidate = match.group(2).strip()
    words = [w.strip(".") for w in candidate.split()]
    if not words:
        return match.group(0)
    # "my name is X" is always treated as a name; "I am / this is" skips clinical/status adjectives.
    lowered_prefix = prefix.lower()
    if "name" not in lowered_prefix and words[0].lower() in _CHAT_NON_NAME_WORDS:
        return match.group(0)
    return f"{prefix}[REDACTED_NAME]"


def minimize_to_result_lines(raw_text: str) -> Tuple[str, Dict[str, Any]]:
    """
    Keep only lines containing a known biomarker alias or a number+unit measurement,
    plus +-1 line of non-PII context for split table rows. Drops headers, footers,
    signatures, addresses, barcodes, and demographics.
    """
    if not raw_text or not raw_text.strip():
        return "", {"total_lines": 0, "matched_lines": 0, "kept_lines": 0}

    lines = raw_text.splitlines()
    matched_indices = set()

    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        has_alias = bool(_BIOMARKER_ALIAS_REGEX.search(stripped))
        has_num_unit = bool(_NUMBER_UNIT_REGEX.search(stripped))
        # Guard against lines like "Age: 42 yrs" or header dates matching spurious units
        if (has_alias or has_num_unit) and not _NON_RESULT_CONTEXT_LINE.search(stripped):
            matched_indices.add(idx)

    if not matched_indices:
        return "", {
            "total_lines": len(lines),
            "matched_lines": 0,
            "kept_lines": 0,
        }

    kept_indices = set(matched_indices)
    for idx in matched_indices:
        for neighbor in (idx - 1, idx + 1):
            if 0 <= neighbor < len(lines):
                neighbor_stripped = lines[neighbor].strip()
                if neighbor_stripped and not _NON_RESULT_CONTEXT_LINE.search(neighbor_stripped):
                    kept_indices.add(neighbor)

    kept_lines = [lines[i] for i in sorted(kept_indices)]
    return "\n".join(kept_lines), {
        "total_lines": len(lines),
        "matched_lines": len(matched_indices),
        "kept_lines": len(kept_lines),
    }


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
    # Labeled Patient / Hospital / Lab / Barcode / Accession / Specimen identifiers
    (
        "id",
        re.compile(
            r"(?i)\b(uhid|mrn|patient\s*id|pt\.?\s*id|reg(?:istration)?\s*(?:no|id|#)|"
            r"lab\s*(?:no|id|ref)|sample\s*id|specimen\s*(?:no|id)?|order\s*(?:no|id)?|"
            r"bill\s*(?:no|id)?|receipt\s*(?:no|id)?|barcode(?:\s*(?:no|id))?|bar\s*code|"
            r"accession\s*(?:no|id|#)?|acc\s*(?:no|id|#)|passport\s*(?:no|id)?|ssn)"
            r"\s*[:|#.-]*\s*[A-Z0-9][A-Z0-9/_-]{2,24}"
        ),
        r"\1: [REDACTED_ID]",
    ),
    # Bracketed/starred barcode strings such as *BC8849201* or [BC-99210]
    (
        "id",
        re.compile(r"\*[A-Z0-9-]{5,24}\*"),
        "[REDACTED_ID]",
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
    # Labeled phone numbers / helplines / landlines
    (
        "phone",
        re.compile(r"(?i)\b(phone|ph|mob|mobile|tel|telephone|helpline|landline|fax|call|contact(?:\s+no)?)\s*[:|.]?\s*(?:\+?\d[\d\s().-]{6,16}\d)"),
        r"\1: [REDACTED_PHONE]",
    ),
    # Indian +91 / 10-digit mobile numbers (starting 6-9), STD landlines, and US 10-digit phones
    (
        "phone",
        re.compile(r"(?:\+91[\s-]?)?\b[6-9]\d{4}[\s-]?\d{5}\b"),
        "[REDACTED_PHONE]",
    ),
    (
        "phone",
        re.compile(r"\b0\d{2,4}[-\s]\d{6,8}\b"),
        "[REDACTED_PHONE]",
    ),
    (
        "phone",
        re.compile(r"\b\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    # Relational guardian/parent lines: S/O, D/O, W/O, C/O
    (
        "name",
        re.compile(
            r"(?i)\b((?:s/o|d/o|w/o|c/o)\s*[:|.]?\s*)"
            r"([A-Za-z][A-Za-z.\s'-]{1,45}?)(?=\s*(?:\r?\n|,|\||age\b|gender\b|sex\b|dob\b|date\b|$))"
        ),
        r"\1[REDACTED_NAME]",
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
    # Unlabelled honorific names (Mr., Mrs., Ms., Miss, Smt., Shri)
    (
        "name",
        re.compile(
            r"(?i)\b((?:mr|mrs|ms|miss|smt|shri)\.?\s+)"
            r"([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,3})"
            r"(?=\s*(?:\r?\n|,|\||s/o\b|d/o\b|w/o\b|age\b|gender\b|sex\b|dob\b|date\b|$))"
        ),
        "[REDACTED_NAME]",
    ),
    # Labeled referring physician / pathologist / verifier signatures
    (
        "name",
        re.compile(
            r"(?i)\b((?:ref(?:erred)?\s*by|consultant|ordering\s+physician|pathologist|verified\s+by|signed\s+by|doctor)\s*[:|]?\s*)"
            r"((?:Dr\.?\s+)?[A-Za-z][A-Za-z.\s'-]{1,50}?)(?=\s*(?:\r?\n|,|\||$))"
        ),
        r"\1[REDACTED_DOCTOR]",
    ),
    # Standalone Dr. <Person Name> signatures (do not match "Dr Lal PathLabs" lab brand unless followed by MD/person name)
    (
        "name",
        re.compile(
            r"\bDr\.?\s+(?!Lal\s+PathLabs\b)([A-Z][A-Za-z.]*(?:\s+[A-Z][A-Za-z.]*){1,3})"
            r"(?:\s*,\s*(?:MD|MBBS|DNB|PhD|Patholog[a-z]*))?"
        ),
        "[REDACTED_DOCTOR]",
    ),
    # Chat self-introduction phrases ("my name is Ravi", "I am Aarav Sharma", "this is Meera")
    (
        "name",
        re.compile(
            r"(?i)\b(my\s+name\s+is\s+|call\s+me\s+)([A-Za-z][A-Za-z.'-]*(?:\s+[A-Za-z][A-Za-z.'-]*){0,2})"
            r"(?=\s*(?:\r?\n|[,.!?;]|and\b|age\b|$))"
        ),
        _redact_chat_self_intro,
    ),
    (
        "name",
        re.compile(
            r"\b((?:[Ii]\s+am|[Ii]'m|[Tt]his\s+is)\s+)((?:(?:Mr|Mrs|Ms|Dr)\.?\s+)?[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,2})"
            r"(?=\s*(?:\r?\n|[,.!?;]|and\b|age\b|$))"
        ),
        _redact_chat_self_intro,
    ),
    # Labeled street / home addresses
    (
        "address",
        re.compile(r"(?i)\b(address|addr|residence)\s*[:|]\s*[^\r\n]{4,140}"),
        r"\1: [REDACTED_ADDRESS]",
    ),
    # Unlabelled street/locality addresses containing common road/sector/flat cues or 6-digit Indian pincode
    (
        "address",
        re.compile(
            r"(?im)^(?=[^\r\n]*\b(?:road|rd\.?|street|st\.?|marg|nagar|colony|vihar|enclave|sector|phase|block|flat|house\s+no|apt|apartments|lane|layout|bengaluru|bangalore|mumbai|delhi|chennai|kolkata|hyderabad|pune|noida|gurgaon|gurugram|[1-8]\d{5})\b)"
            r"[^\r\n]*(?:,\s*[^\r\n]+|\b[1-8]\d{5}\b)[^\r\n]*$"
        ),
        "[REDACTED_ADDRESS]",
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
