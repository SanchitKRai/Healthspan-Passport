import pytest
from pathlib import Path


def test_benchmark_metrics_calculation_logic():
    from scripts.benchmark_extraction import evaluate_extraction_against_ground_truth

    ground_truth_item = {
        "glucose_fasting": {"value": 100.0, "unit": "mg/dL"},
        "albumin": {"value": 4.5, "unit": "g/dL"},
        "creatinine": {"value": 1.0, "unit": "mg/dL"},
    }

    # Case 1: 2 correct, 1 wrong but flagged with needs_review=True (safe)
    extracted_items = [
        {"standard_id": "glucose_fasting", "value": 100.0, "unit": "mg/dL", "needs_review": False},
        {"standard_id": "albumin", "value": 4.5, "unit": "g/dL", "needs_review": False},
        {"standard_id": "creatinine", "value": 1.9, "unit": "mg/dL", "needs_review": True},
    ]

    metrics = evaluate_extraction_against_ground_truth(extracted_items, ground_truth_item)
    assert metrics["total_expected"] == 3
    assert metrics["matched_count"] == 2
    assert metrics["unflagged_errors"] == 0
    assert metrics["flagged_count"] == 1

    # Case 2: 1 wrong value NOT flagged (unflagged error - dangerous)
    extracted_unsafe = [
        {"standard_id": "glucose_fasting", "value": 100.0, "unit": "mg/dL", "needs_review": False},
        {"standard_id": "albumin", "value": 14.5, "unit": "g/dL", "needs_review": False}, # wrong & unflagged!
    ]
    metrics_unsafe = evaluate_extraction_against_ground_truth(extracted_unsafe, ground_truth_item)
    assert metrics_unsafe["unflagged_errors"] == 1
