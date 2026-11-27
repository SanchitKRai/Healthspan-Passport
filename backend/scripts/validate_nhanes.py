"""
Synthetic Cohort Unit-Test Helper for PhenoAge Code Path

WARNING / INTEGRITY NOTICE:
This script generates a SYNTHETIC cohort and simulates mortality directly from
the Levine et al. (2018) coefficients themselves. Correlation and hazard ratios
computed on this data are circular by construction and MUST NOT be treated as
clinical or epidemiological validation. It exists solely to unit-test the
scoring, quartile-bucketing, and regression code paths in CI/offline tests.
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
import numpy as np
import pandas as pd
from scipy import stats

# Ensure backend root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from app.core.phenoage import (
    calculate_phenoage,
    LEVINE_INTERCEPT,
    COEFFICIENTS,
    GOMPERTZ_FACTOR,
)


def generate_synthetic_test_cohort(n_samples: int = 10724, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a SYNTHETIC cohort for unit-testing the PhenoAge scoring and statistics
    code paths. Mortality is simulated from Levine coefficients (circular by design;
    NOT real NHANES data and NOT validation).
    """
    rng = np.random.default_rng(random_seed)

    age = np.clip(rng.normal(loc=48.5, scale=16.5, size=n_samples), 20.0, 84.0)
    std_age = (age - 48.5) / 16.5
    latent_frailty = rng.normal(loc=0.0, scale=0.85, size=n_samples)

    albumin = np.clip(43.5 - 1.2 * std_age - 1.5 * latent_frailty + rng.normal(0, 2.5, n_samples), 25.0, 55.0)
    creatinine = np.clip(80.0 + 6.5 * std_age + 8.0 * latent_frailty + rng.normal(0, 12.0, n_samples), 40.0, 300.0)
    glucose = np.clip(5.2 + 0.5 * std_age + 0.6 * latent_frailty + rng.lognormal(0.0, 0.25, n_samples) - 1.0, 3.5, 18.0)

    log_crp = -2.0 + 0.35 * std_age + 0.55 * latent_frailty + rng.normal(0, 0.75, n_samples)
    crp = np.clip(np.exp(log_crp), 0.01, 10.0)

    lymphocyte_pct = np.clip(31.5 - 2.0 * std_age - 2.2 * latent_frailty + rng.normal(0, 5.0, n_samples), 8.0, 60.0)
    mcv = np.clip(89.5 + 1.1 * std_age + 0.8 * latent_frailty + rng.normal(0, 3.8, n_samples), 70.0, 115.0)
    rdw = np.clip(12.7 + 0.3 * std_age + 0.45 * latent_frailty + rng.normal(0, 0.8, n_samples), 10.5, 22.0)
    alp = np.clip(72.0 + 4.5 * std_age + 5.5 * latent_frailty + rng.normal(0, 16.0, n_samples), 30.0, 250.0)
    wbc = np.clip(6.9 + 0.2 * std_age + 0.6 * latent_frailty + rng.normal(0, 1.8, n_samples), 2.5, 20.0)

    # Simulated 10-year mortality derived from Levine formula (circular; for code-path testing only)
    ln_crp_arr = np.log(crp)
    true_xb = (
        LEVINE_INTERCEPT
        + COEFFICIENTS["albumin"] * albumin
        + COEFFICIENTS["creatinine"] * creatinine
        + COEFFICIENTS["glucose"] * glucose
        + COEFFICIENTS["crp"] * ln_crp_arr
        + COEFFICIENTS["lymphocyte_pct"] * lymphocyte_pct
        + COEFFICIENTS["mcv"] * mcv
        + COEFFICIENTS["rdw"] * rdw
        + COEFFICIENTS["alp"] * alp
        + COEFFICIENTS["wbc"] * wbc
        + COEFFICIENTS["age"] * age
    )

    p_mort_10yr = 1.0 - np.exp(-np.exp(true_xb) * GOMPERTZ_FACTOR)
    p_mort_10yr = np.clip(p_mort_10yr, 0.001, 0.999)

    mortstat = (rng.uniform(0, 1, size=n_samples) < p_mort_10yr).astype(int)

    followup_months = np.full(n_samples, 120.0)
    died_idx = np.where(mortstat == 1)[0]
    followup_months[died_idx] = np.clip(
        rng.weibull(a=1.5, size=len(died_idx)) * 60.0 + 1.0, 1.0, 120.0
    )

    return pd.DataFrame({
        "subject_id": np.arange(10001, 10001 + n_samples),
        "age": np.round(age, 1),
        "albumin": np.round(albumin, 1),
        "creatinine": np.round(creatinine, 1),
        "glucose": np.round(glucose, 2),
        "crp": np.round(crp, 3),
        "lymphocyte_pct": np.round(lymphocyte_pct, 1),
        "mcv": np.round(mcv, 1),
        "rdw": np.round(rdw, 1),
        "alp": np.round(alp, 1),
        "wbc": np.round(wbc, 2),
        "mortstat": mortstat,
        "followup_months": np.round(followup_months, 1),
    })


def score_synthetic_cohort(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies our exact Levine et al. (2018) PhenoAge implementation to every row.
    """
    scored = df.copy()
    phenoages = []
    age_accels = []
    mort_scores = []

    for _, row in scored.iterrows():
        bio_dict = {
            "albumin": row["albumin"],
            "creatinine": row["creatinine"],
            "glucose": row["glucose"],
            "crp": row["crp"],
            "lymphocyte_pct": row["lymphocyte_pct"],
            "mcv": row["mcv"],
            "rdw": row["rdw"],
            "alp": row["alp"],
            "wbc": row["wbc"],
        }
        res = calculate_phenoage(bio_dict, float(row["age"]))
        phenoages.append(res["phenoage"])
        age_accels.append(res["age_acceleration"])
        mort_scores.append(res["mortality_score_10yr"])

    scored["phenoage"] = phenoages
    scored["age_acceleration"] = age_accels
    scored["mortality_score_10yr"] = mort_scores
    return scored


def calculate_quartile_mortality(scored_df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calculates mortality summary statistics across PhenoAge acceleration quartiles.
    """
    df = scored_df.dropna(subset=["age_acceleration", "mortstat"]).copy()
    df["quartile"] = pd.qcut(
        df["age_acceleration"],
        q=4,
        labels=["Q1 (Decelerated)", "Q2 (Normal-Low)", "Q3 (Normal-High)", "Q4 (Accelerated)"]
    )

    quartile_metrics = []
    base_mortality_rate = None

    for q_label, group in df.groupby("quartile", observed=True):
        n = len(group)
        deaths = int(group["mortstat"].sum())
        mort_rate = (deaths / n) * 100.0 if n > 0 else 0.0

        if base_mortality_rate is None and n > 0:
            base_mortality_rate = mort_rate if mort_rate > 0 else 1.0

        rel_risk = mort_rate / base_mortality_rate if base_mortality_rate else 1.0

        quartile_metrics.append({
            "quartile": str(q_label),
            "n": n,
            "deaths": deaths,
            "mortality_rate_pct": round(mort_rate, 2),
            "relative_risk_vs_q1": round(rel_risk, 2),
            "mean_chronological_age": round(float(group["age"].mean()), 1),
            "mean_phenoage": round(float(group["phenoage"].mean()), 1),
            "mean_acceleration": round(float(group["age_acceleration"].mean()), 2),
            "accel_min": round(float(group["age_acceleration"].min()), 1),
            "accel_max": round(float(group["age_acceleration"].max()), 1),
        })

    return quartile_metrics


def compute_cohort_statistics(scored_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes Pearson correlation r and Cox proportional hazards regression
    on a scored cohort dataframe.
    """
    if "phenoage" not in scored_df.columns:
        scored_df = score_synthetic_cohort(scored_df)

    df = scored_df.dropna(subset=["phenoage", "age", "mortstat", "followup_months"]).copy()

    r, p_val = stats.pearsonr(df["age"], df["phenoage"])

    cox_hr = None
    ci_lower = None
    ci_upper = None
    cox_p = None

    from statsmodels.duration.hazard_regression import PHReg
    ph_model = PHReg(
        endog=df["followup_months"],
        exog=df[["age_acceleration", "age"]],
        status=df["mortstat"]
    )
    res = ph_model.fit()
    param = res.params[0] if isinstance(res.params, np.ndarray) else res.params.iloc[0]
    cox_hr = float(np.exp(param))

    conf = res.conf_int()
    lower_val = conf[0][0] if isinstance(conf, np.ndarray) else conf.iloc[0, 0]
    upper_val = conf[0][1] if isinstance(conf, np.ndarray) else conf.iloc[0, 1]
    ci_lower = float(np.exp(lower_val))
    ci_upper = float(np.exp(upper_val))
    cox_p = float(res.pvalues[0] if isinstance(res.pvalues, np.ndarray) else res.pvalues.iloc[0])

    return {
        "sample_size": len(df),
        "pearson_r": round(float(r), 4),
        "pearson_p_value": float(p_val),
        "mean_age": round(float(df["age"].mean()), 1),
        "mean_phenoage": round(float(df["phenoage"].mean()), 1),
        "overall_10yr_mortality_pct": round(float(df["mortstat"].mean() * 100.0), 2),
        "cox_hazard_ratio_per_year": round(cox_hr, 3),
        "cox_ci_95": (round(ci_lower, 3), round(ci_upper, 3)),
        "cox_p_value": cox_p,
    }


def run_synthetic_unit_test(
    data_csv_path: Path = BASE_DIR.parent / "data" / "synthetic_cohort_unit_test.csv",
) -> Dict[str, Any]:
    """
    Executes the PhenoAge scoring pipeline on the synthetic unit-test cohort.
    """
    print("=" * 70)
    print("Running PhenoAge Code-Path Smoke Test on SYNTHETIC Cohort (NOT Validation)")
    print("=" * 70)

    if data_csv_path.exists():
        print(f"Loading existing synthetic test cohort from {data_csv_path}...")
        df = pd.read_csv(data_csv_path)
    else:
        print("Generating synthetic unit-test cohort (N=10,724)...")
        df = generate_synthetic_test_cohort(n_samples=10724, random_seed=42)
        data_csv_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(data_csv_path, index=False)
        print(f"Saved synthetic test cohort to {data_csv_path}")

    scored_df = score_synthetic_cohort(df)
    stats_dict = compute_cohort_statistics(scored_df)
    quartiles = calculate_quartile_mortality(scored_df)

    print(f"Synthetic Sample Size (N): {stats_dict['sample_size']:,}")
    print(f"Quartiles computed: {len(quartiles)}")
    print("Synthetic unit-test cohort run complete (results are circular; not validation).")
    return {
        "stats": stats_dict,
        "quartiles": quartiles,
    }


if __name__ == "__main__":
    run_synthetic_unit_test()
