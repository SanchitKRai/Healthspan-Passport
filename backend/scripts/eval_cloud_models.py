"""
Part A benchmark: Compare candidate OpenRouter slugs on N=3 synthetic reports
(1 digital PDF + 2 phone photos) with provider.data_collection='deny',
temperature=0, max_tokens=2000, and structured JSON output.
Also supports evaluating a chosen single primary model across all 15 synthetic
dev-set reports (N=15).
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from dotenv import load_dotenv
import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.extraction.extractor import extract_text_from_file
from app.llm.client import OPENROUTER_API_URL, parse_and_validate_extraction, prepare_outbound_extraction_text
from app.llm.prompts import SYSTEM_PROMPT, build_extraction_prompt

GROUND_TRUTH_PATH = REPO_ROOT / "data" / "ground_truth.json"
SAMPLE_DIR = REPO_ROOT / "data" / "sample_reports"

N3_REPORTS = [
    "01_dr_lal_healthy_adult.pdf",
    "09_phone_photo_cbc_skewed.jpg",
    "10_phone_photo_metabolic_shadow.jpg",
]

CANDIDATE_MODELS = [
    "mistralai/mistral-small-3.2-24b-instruct",
    "openai/gpt-4o-mini",
]


def _fetch_model_pricing() -> dict:
    req = urllib.request.Request("https://openrouter.ai/api/v1/models", headers={"User-Agent": "HP"})
    with urllib.request.urlopen(req, timeout=20) as r:
        models = json.loads(r.read().decode("utf-8"))["data"]
    return {m["id"]: m.get("pricing", {}) for m in models}


def _match_against_gt(resp, gt_bio: dict) -> tuple[int, list]:
    matched = 0
    matched_ids = []
    # Also normalize units if LLM converted them (e.g. g/L -> g/dL or umol/L -> mg/dL? Compare canonical numeric or direct value)
    for bio in resp.biomarkers:
        std_id = bio.standard_id.value if hasattr(bio.standard_id, "value") else str(bio.standard_id)
        if std_id in gt_bio and bio.value is not None:
            gt_val = gt_bio[std_id]["value"]
            if abs(bio.value - gt_val) < 0.05 * (abs(gt_val) + 1e-5):
                matched += 1
                matched_ids.append(std_id)
    return matched, matched_ids


def _sanitize_error(text: str) -> str:
    cleaned = re.sub(r"https://openrouter\.ai/workspaces/[^\s\"']+", "https://openrouter.ai/workspaces/[REDACTED]", text)
    cleaned = re.sub(r'"user_id"\s*:\s*"[^"]+"', '"user_id":"[REDACTED]"', cleaned)
    return cleaned[:400]


def evaluate_model_on_reports(
    model_slug: str,
    reports: list[str],
    api_key: str,
    pricing: dict,
    gt_all: dict,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/SanchitKRai/Healthspan-Passport",
        "X-Title": "Healthspan Passport",
        "Content-Type": "application/json",
    }
    p_info = pricing.get(model_slug, {})
    p_prompt = float(p_info.get("prompt", 0.0))
    p_comp = float(p_info.get("completion", 0.0))

    rows = []
    for fname in reports:
        gt_bio = gt_all[fname]["biomarkers"]
        raw_text, _ = extract_text_from_file((SAMPLE_DIR / fname).read_bytes(), fname)
        outbound_text, prep_stats = prepare_outbound_extraction_text(raw_text)
        prompt = build_extraction_prompt(outbound_text)

        payload = {
            "model": model_slug,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 2000,
            "response_format": {"type": "json_object"},
            "provider": {"data_collection": "deny"},
        }

        t0 = time.time()
        valid_json = False
        success = False
        extracted_count = 0
        matched_count = 0
        prompt_tokens = 0
        completion_tokens = 0
        cost_usd = None
        err = None

        try:
            with httpx.Client(timeout=45.0) as client:
                resp = client.post(OPENROUTER_API_URL, headers=headers, json=payload)
            latency_ms = int((time.time() - t0) * 1000)
            if resp.status_code >= 400:
                err = f"HTTP {resp.status_code}: {_sanitize_error(resp.text)}"
            else:
                body = resp.json()
                usage = body.get("usage") or {}
                prompt_tokens = int(usage.get("prompt_tokens") or 0)
                completion_tokens = int(usage.get("completion_tokens") or 0)
                if "cost" in usage and usage["cost"] is not None:
                    cost_usd = round(float(usage["cost"]), 8)
                else:
                    cost_usd = round(prompt_tokens * p_prompt + completion_tokens * p_comp, 8)

                content = (body.get("choices") or [{}])[0].get("message", {}).get("content")
                if not isinstance(content, str) or not content.strip():
                    err = f"Empty content (finish_reason={(body.get('choices') or [{}])[0].get('finish_reason')})"
                else:
                    parsed = parse_and_validate_extraction(content, outbound_text, model_slug, latency_ms)
                    valid_json = True
                    success = True
                    extracted_count = len(parsed.biomarkers)
                    matched_count, _ = _match_against_gt(parsed, gt_bio)
        except Exception as exc:
            latency_ms = int((time.time() - t0) * 1000)
            err = f"{type(exc).__name__}: {_sanitize_error(str(exc))}"

        expected_count = len(gt_bio)
        rows.append({
            "report": fname,
            "format": "digital_pdf" if fname.endswith(".pdf") else "phone_photo",
            "success": success,
            "valid_json": valid_json,
            "expected_fields": expected_count,
            "extracted_fields": extracted_count,
            "matched_fields": matched_count,
            "accuracy_pct": round((matched_count / max(1, expected_count)) * 100.0, 1),
            "latency_ms": latency_ms,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "cost_usd": cost_usd,
            "kept_lines": prep_stats.get("kept_lines"),
            "error": err,
        })

    total_exp = sum(r["expected_fields"] for r in rows)
    total_match = sum(r["matched_fields"] for r in rows)
    valid_costs = [r["cost_usd"] for r in rows if r["cost_usd"] is not None]
    avg_lat = round(sum(r["latency_ms"] for r in rows) / max(1, len(rows)), 1)
    avg_cost = round(sum(valid_costs) / len(valid_costs), 8) if valid_costs else None
    total_cost = round(sum(valid_costs), 8) if valid_costs else None

    return {
        "model": model_slug,
        "reports_tested": len(rows),
        "success_count": sum(1 for r in rows if r["success"]),
        "valid_json_count": sum(1 for r in rows if r["valid_json"]),
        "total_expected_fields": total_exp,
        "total_matched_fields": total_match,
        "overall_accuracy_pct": round((total_match / max(1, total_exp)) * 100.0, 1),
        "pdf_accuracy_pct": round(
            sum(r["matched_fields"] for r in rows if r["format"] == "digital_pdf")
            / max(1, sum(r["expected_fields"] for r in rows if r["format"] == "digital_pdf"))
            * 100.0,
            1,
        ),
        "photo_accuracy_pct": round(
            sum(r["matched_fields"] for r in rows if r["format"] == "phone_photo")
            / max(1, sum(r["expected_fields"] for r in rows if r["format"] == "phone_photo"))
            * 100.0,
            1,
        ),
        "avg_latency_ms": avg_lat,
        "avg_cost_per_call_usd": avg_cost,
        "total_cost_usd": total_cost,
        "results": rows,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["n3_compare", "n15_dev"], default="n3_compare")
    parser.add_argument("--model", default="mistralai/mistral-small-3.2-24b-instruct")
    parser.add_argument("--tag", default="baseline")
    parser.add_argument("--out", default=None)
    args = parser.parse_args()

    load_dotenv(BACKEND_DIR / ".env")
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("ERROR: OPENROUTER_API_KEY missing.", file=sys.stderr)
        sys.exit(1)

    gt_all = json.loads(GROUND_TRUTH_PATH.read_text(encoding="utf-8"))
    pricing = _fetch_model_pricing()

    if args.mode == "n3_compare":
        out_path = Path(args.out) if args.out else (REPO_ROOT / "data" / "results" / "cloud_model_comparison_n3.json")
        comparisons = [
            evaluate_model_on_reports(m, N3_REPORTS, api_key, pricing, gt_all)
            for m in CANDIDATE_MODELS
        ]
        payload = {
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scope": "N=3, synthetic reports, early comparison (data_collection=deny, temperature=0, max_tokens=2000)",
            "reports": N3_REPORTS,
            "models": comparisons,
        }
    else:
        out_path = Path(args.out) if args.out else (REPO_ROOT / "data" / "results" / f"cloud_dev_n15_{args.tag}.json")
        all_reports = sorted(gt_all.keys())
        summary = evaluate_model_on_reports(args.model, all_reports, api_key, pricing, gt_all)
        payload = {
            "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "scope": "development set, synthetic, N=15",
            "tag": args.tag,
            "data_collection_setting": "deny",
            **summary,
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
