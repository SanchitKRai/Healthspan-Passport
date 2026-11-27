import os
import sys
import time
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.extraction.extractor import extract_text_from_file
from app.llm.client import call_openrouter_api, parse_and_validate_extraction
from app.llm.prompts import build_extraction_prompt
from app.llm.redact import redact_pii

SAMPLE_DIR = REPO_ROOT / "data" / "sample_reports"
GROUND_TRUTH_FILE = REPO_ROOT / "data" / "ground_truth.json"
RESULTS_FILE = REPO_ROOT / "docs" / "BAKEOFF_RESULTS.md"

REPRESENTATIVE_REPORTS = [
    "01_dr_lal_healthy_adult.pdf",
    "02_metropolis_prediabetic.pdf",
    "06_quest_missing_crp.pdf",
    "09_phone_photo_cbc_skewed.jpg",
    "10_phone_photo_metabolic_shadow.jpg",
]

MODELS_TO_COMPARE = [
    {"name": "Nemotron (Primary)", "slug": os.getenv("OPENROUTER_PRIMARY_MODEL", "nvidia/nemotron-3.5-lightning")},
    {"name": "Kimi (Fallback)", "slug": os.getenv("OPENROUTER_FALLBACK_MODEL", "moonshotai/kimi-k2")},
]


def run_bakeoff():
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print(
            "ERROR: OPENROUTER_API_KEY environment variable is not set.\n"
            "The model bake-off requires live OpenRouter API calls to compare LLM models "
            "and will not substitute offline heuristic results or hardcoded latencies.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    print("=" * 70)
    print("HEALTHSPAN PASSPORT - EXTRACTION MODEL BAKE-OFF (LIVE OPENROUTER API)")
    print(f"Comparing: {[m['name'] + ' (' + m['slug'] + ')' for m in MODELS_TO_COMPARE]}")
    print(f"Test Set: {len(REPRESENTATIVE_REPORTS)} synthetic reports (PDFs + mobile photos)")
    print("=" * 70)

    results = []

    for report_name in REPRESENTATIVE_REPORTS:
        report_path = SAMPLE_DIR / report_name
        gt = ground_truth.get(report_name, {})
        gt_biomarkers = gt.get("biomarkers", {})
        total_expected = len(gt_biomarkers)

        print(f"\nEvaluating: {report_name} (Expected biomarkers: {total_expected})")
        file_bytes = report_path.read_bytes()
        raw_text, _ = extract_text_from_file(file_bytes, report_name)

        for model_info in MODELS_TO_COMPARE:
            m_name = model_info["name"]
            m_slug = model_info["slug"]

            t_start = time.time()
            extracted_count = 0
            accuracy_hits = 0
            valid_json = True
            error_msg = None

            try:
                redacted_text, _ = redact_pii(raw_text)
                prompt = build_extraction_prompt(redacted_text)
                raw_resp = call_openrouter_api(m_slug, prompt, api_key, timeout=45.0)
                duration_ms = int((time.time() - t_start) * 1000)
                resp = parse_and_validate_extraction(raw_resp, redacted_text, m_slug, duration_ms)
                extracted_count = len(resp.biomarkers)

                for bio in resp.biomarkers:
                    std_id = bio.standard_id.value if hasattr(bio.standard_id, "value") else str(bio.standard_id)
                    if std_id in gt_biomarkers:
                        gt_val = gt_biomarkers[std_id]["value"]
                        if bio.value is not None and abs(bio.value - gt_val) < 0.05 * (gt_val + 1e-5):
                            accuracy_hits += 1

            except Exception as e:
                duration_ms = int((time.time() - t_start) * 1000)
                valid_json = False
                error_msg = str(e)

            accuracy_pct = round((accuracy_hits / max(1, total_expected)) * 100, 1)

            results.append({
                "report": report_name,
                "model": m_name,
                "slug": m_slug,
                "expected_fields": total_expected,
                "extracted_fields": extracted_count,
                "matched_fields": accuracy_hits,
                "accuracy_pct": accuracy_pct,
                "latency_ms": duration_ms,
                "valid_json": valid_json,
                "error": error_msg,
            })

            print(f"  -> {m_name}: {accuracy_hits}/{total_expected} fields ({accuracy_pct}%), latency={duration_ms}ms, valid_json={valid_json}")

    md_lines = [
        "# Healthspan Passport - Model Bake-Off Results",
        "",
        f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}",
        "**Environment:** OpenRouter Live API (against 5 synthetic sample reports)",
        "",
        "## Summary by Model",
        "",
        "| Model | Slug | Avg Accuracy (%) | Avg Latency (ms) | Schema Pass Rate |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ]

    for model_info in MODELS_TO_COMPARE:
        m_name = model_info["name"]
        m_slug = model_info["slug"]
        m_res = [r for r in results if r["model"] == m_name]
        avg_acc = round(sum(r["accuracy_pct"] for r in m_res) / len(m_res), 1)
        avg_lat = round(sum(r["latency_ms"] for r in m_res) / len(m_res), 0)
        pass_rate = f"{round((sum(1 for r in m_res if r['valid_json']) / len(m_res)) * 100)}%"
        md_lines.append(f"| {m_name} | `{m_slug}` | **{avg_acc}%** | {int(avg_lat)} ms | {pass_rate} |")

    md_lines.extend([
        "",
        "## Detailed Report Breakdown",
        "",
        "| Report File | Model | Expected | Extracted | Matched | Accuracy | Latency | Valid JSON |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for r in results:
        md_lines.append(
            f"| `{r['report']}` | {r['model']} | {r['expected_fields']} | {r['extracted_fields']} | {r['matched_fields']} | {r['accuracy_pct']}% | {r['latency_ms']} ms | {'✅' if r['valid_json'] else '❌'} |"
        )

    RESULTS_FILE.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nBake-off complete! Detailed results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    run_bakeoff()
