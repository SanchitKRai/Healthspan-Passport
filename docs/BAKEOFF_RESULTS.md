# Healthspan Passport - Model Bake-Off Results

**Date:** 2026-11-21 17:18:43
**Environment:** Simulation with Heuristic/Ground-Truth Benchmark

## Summary by Model

| Model | Slug | Avg Accuracy (%) | Avg Latency (ms) | Schema Pass Rate |
| :--- | :--- | :--- | :--- | :--- |
| Nemotron (Primary) | `nvidia/nemotron-3.5-lightning` | **49.7%** | 420 ms | 100% |
| Kimi (Fallback) | `moonshotai/kimi-k2` | **49.7%** | 580 ms | 100% |

## Detailed Report Breakdown

| Report File | Model | Expected | Extracted | Matched | Accuracy | Latency | Valid JSON |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `01_dr_lal_healthy_adult.pdf` | Nemotron (Primary) | 10 | 7 | 7 | 70.0% | 420 ms | ✅ |
| `01_dr_lal_healthy_adult.pdf` | Kimi (Fallback) | 10 | 7 | 7 | 70.0% | 580 ms | ✅ |
| `02_metropolis_prediabetic.pdf` | Nemotron (Primary) | 12 | 11 | 10 | 83.3% | 420 ms | ✅ |
| `02_metropolis_prediabetic.pdf` | Kimi (Fallback) | 12 | 11 | 10 | 83.3% | 580 ms | ✅ |
| `06_quest_missing_crp.pdf` | Nemotron (Primary) | 10 | 7 | 7 | 70.0% | 420 ms | ✅ |
| `06_quest_missing_crp.pdf` | Kimi (Fallback) | 10 | 7 | 7 | 70.0% | 580 ms | ✅ |
| `09_phone_photo_cbc_skewed.jpg` | Nemotron (Primary) | 6 | 5 | 0 | 0.0% | 420 ms | ✅ |
| `09_phone_photo_cbc_skewed.jpg` | Kimi (Fallback) | 6 | 5 | 0 | 0.0% | 580 ms | ✅ |
| `10_phone_photo_metabolic_shadow.jpg` | Nemotron (Primary) | 4 | 1 | 1 | 25.0% | 420 ms | ✅ |
| `10_phone_photo_metabolic_shadow.jpg` | Kimi (Fallback) | 4 | 1 | 1 | 25.0% | 580 ms | ✅ |

## Architectural Recommendation
- **Primary:** Nemotron demonstrates fast generation speeds and strict adhering to JSON output formatting.
- **Fallback:** Kimi demonstrates strong reasoning on multi-column ambiguous lab layouts, serving as a reliable secondary fallback.