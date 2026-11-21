import pytest
import numpy as np
import pandas as pd


def test_nhanes_cohort_scoring_logic():
    from scripts.validate_nhanes import score_nhanes_cohort, calculate_quartile_mortality

    # Create synthetic cohort with known properties
    df = pd.DataFrame({
        "age": [30.0, 45.0, 60.0, 75.0],
        "albumin": [46.0, 43.0, 40.0, 37.0],
        "creatinine": [75.0, 85.0, 95.0, 110.0],
        "glucose": [4.8, 5.2, 5.8, 6.5],
        "crp": [0.05, 0.12, 0.25, 0.50],
        "lymphocyte_pct": [35.0, 30.0, 26.0, 20.0],
        "mcv": [88.0, 90.0, 92.0, 95.0],
        "rdw": [12.0, 12.8, 13.5, 14.8],
        "alp": [65.0, 75.0, 85.0, 105.0],
        "wbc": [5.5, 6.5, 7.5, 8.8],
        "mortstat": [0, 0, 1, 1], # 10-year mortality status
        "followup_months": [120.0, 120.0, 72.0, 36.0],
    })

    scored_df = score_nhanes_cohort(df)
    assert "phenoage" in scored_df.columns
    assert "age_acceleration" in scored_df.columns
    assert not scored_df["phenoage"].isnull().any()

    # Older subjects with higher biomarkers should have higher PhenoAge
    assert scored_df["phenoage"].iloc[3] > scored_df["phenoage"].iloc[0]

    # Quartile analysis
    quartiles = calculate_quartile_mortality(scored_df)
    assert len(quartiles) > 0
    assert "mortality_rate_pct" in quartiles[0]
    assert "quartile" in quartiles[0]


def test_nhanes_statistical_metrics():
    from scripts.validate_nhanes import compute_cohort_statistics, generate_calibrated_cohort

    # Generate a small sample cohort
    df = generate_calibrated_cohort(n_samples=500, random_seed=42)
    assert len(df) == 500
    assert "age" in df.columns
    assert "mortstat" in df.columns

    stats = compute_cohort_statistics(df)
    assert "pearson_r" in stats
    assert stats["pearson_r"] > 0.85  # Strong correlation with chronological age
    assert "cox_hazard_ratio_per_year" in stats
    assert stats["cox_hazard_ratio_per_year"] > 1.0  # Accelerated aging increases hazard
