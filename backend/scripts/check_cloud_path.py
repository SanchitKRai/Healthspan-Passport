"""
Early N=3 synthetic cloud-path check via OpenRouter with provider.data_collection='deny'.

Tests 1 digital PDF + 2 degraded phone-photo captures from data/sample_reports/
using the live extraction pipeline (minimize -> redact -> OpenRouter).
Writes committed results to data/results/cloud_path_check.json.
"""

import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.extraction.extractor import extract_text_from_file
from app.llm.client import (
    FALLBACK_MODEL,
    OPENROUTER_API_URL,
    PRIMARY_MODEL,
    extract_biomarkers_with_llm,
    parse_and_validate_extraction,
    prepare_outbound_extraction_text,
)
from app.llm.prompts import SYSTEM_PROMPT, build_extraction_prompt

TARGET_REPORTS = [
    "01_dr_lal_healthy_adult.pdf",
    "09_phone_photo_cbc_skewed.jpg",
    "10_phone_photo_metabolic_shadow.jpg",
]
GROUND_TRUTH_PATH = REPO_ROOT / "data" / "ground_truth.json"
OUT_JSON_PATH = REPO_ROOT / "data" / "results" / "cloud_path_check.json"


def run_check() -> None:
    load_dotenv(BACKEND_DIR / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY not found in backend/.env or environment.", file=sys.stderr)
        sys.exit(1)

    gt_all = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    sample_dir = REPO_ROOT / "data" / "sample_reports"

    import httpx

    per_report = []
    for fname in TARGET_REPORTS:
        gt_bio = gt_all[fname]["biomarkers"]
        raw_text, _ = extract_text_from_file((sample_dir / fname).read_bytes(), fname)
        outbound_text, prep_stats = prepare_outbound_extraction_text(raw_text)

        # First run the actual production pipeline
        t0 = time.time()
        res = extract_biomarkers_with_llm(raw_text, api_key=api_key, allow_cloud_llm=True)
        elapsed_ms = int((time.time() - t0) * 1000)

        model_used = res.extraction_metadata.model_used
        used_cloud = not model_used.startswith("heuristic-rule-engine")

        matched = 0
        for bio in res.biomarkers:
            std_id = bio.standard_id.value if hasattr(bio.standard_id, "value") else str(bio.standard_id)
            if std_id in gt_bio and bio.value is not None:
                gt_val = gt_bio[std_id]["value"]
                if abs(bio.value - gt_val) < 0.05 * (abs(gt_val) + 1e-5):
                    matched += 1

        # If pipeline fell back locally, probe primary/fallback directly with data_collection='deny'
        # so we capture exact OpenRouter HTTP error messages for reporting.
        probe_errors = {}
        if not used_cloud:
            prompt = build_extraction_prompt(outbound_text)
            headers = {
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/SanchitKRai/Healthspan-Passport",
                "X-Title": "Healthspan Passport",
                "Content-Type": "application/json",
            }
            for candidate in [PRIMARY_MODEL, FALLBACK_MODEL]:
                payload = {
                    "model": candidate,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 4096,
                    "provider": {"data_collection": "deny"},
                }
                if "kimi-k2" not in candidate.lower():
                    payload["response_format"] = {"type": "json_object"}
                try:
                    with httpx.Client(timeout=45.0) as client:
                        r = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
                        if r.status_code >= 400:
                            import re
                            cleaned_err = re.sub(r"https://openrouter\.ai/workspaces/[^\s\"']+", "https://openrouter.ai/workspaces/[REDACTED]", r.text)
                            cleaned_err = re.sub(r'"user_id"\s*:\s*"[^"]+"', '"user_id":"[REDACTED]"', cleaned_err)
                            probe_errors[candidate] = f"HTTP {r.status_code}: {cleaned_err[:400]}"
                        else:
                            content = (r.json().get("choices") or [{}])[0].get("message", {}).get("content")
                            if not isinstance(content, str) or not content.strip():
                                finish_r = (r.json().get("choices") or [{}])[0].get("finish_reason")
                                probe_errors[candidate] = f"Empty content (finish_reason={finish_r})"
                            else:
                                try:
                                    parse_and_validate_extraction(content, outbound_text, candidate, 0)
                                    probe_errors[candidate] = "unexpectedly succeeded on retry probe"
                                except Exception as pe:
                                    probe_errors[candidate] = f"JSON parse error ({type(pe).__name__}): {str(pe)[:200]}"
                except Exception as exc:
                    probe_errors[candidate] = f"{type(exc).__name__}: {str(exc)[:200]}"

        expected = len(gt_bio)
        acc = round((matched / max(1, expected)) * 100.0, 1)
        per_report.append({
            "report": fname,
            "format": "digital_pdf" if fname.endswith(".pdf") else "phone_photo",
            "model_used": model_used,
            "used_cloud_llm": used_cloud,
            "valid_json_returned": used_cloud,
            "expected_fields": expected,
            "extracted_fields": len(res.biomarkers),
            "matched_fields": matched,
            "accuracy_pct": acc,
            "latency_ms": elapsed_ms,
            "kept_lines": prep_stats.get("kept_lines"),
            "total_lines": prep_stats.get("total_lines"),
            "extracted_sample": [
                {
                    "id": b.standard_id.value if hasattr(b.standard_id, "value") else str(b.standard_id),
                    "value": b.value,
                    "unit": b.unit,
                }
                for b in res.biomarkers[:12]
            ],
            "errors": probe_errors if probe_errors else None,
        })

    total_expected = sum(r["expected_fields"] for r in per_report)
    total_matched = sum(r["matched_fields"] for r in per_report)
    cloud_successes = sum(1 for r in per_report if r["used_cloud_llm"])

    summary = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scope": "N=3, synthetic reports, early check",
        "data_collection_setting": "deny",
        "primary_model": PRIMARY_MODEL,
        "fallback_model": FALLBACK_MODEL,
        "reports_tested": len(per_report),
        "cloud_success_count": cloud_successes,
        "total_expected_fields": total_expected,
        "total_matched_fields": total_matched,
        "overall_accuracy_pct": round((total_matched / max(1, total_expected)) * 100.0, 1),
        "results": per_report,
    }

    OUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    run_check()
