"""
Real CDC NHANES (1999-2010) & NCHS 2019 Linked Mortality Cohort Builder and Analysis.

Merges Demographics (DEMO*), CBC (LAB25/L25/CBC*), Standard Biochemistry Profile
(LAB18/L40/BIOPRO*), CRP (LAB11/L11/CRP*), and NCHS 2019 public-use Linked Mortality
Files on SEQN, computes PhenoAge exclusively by importing `calculate_phenoage`
from `backend/app/core/phenoage.py`, runs unweighted survival analysis with `lifelines`,
and saves:
  - data/results/nhanes_real_results.json
  - docs/nhanes_real_validation.png
  - docs/NHANES_REAL_VALIDATION.md
"""

import json
import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple

import numpy as np
import pandas as pd
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lifelines import CoxPHFitter, KaplanMeierFitter
from lifelines.utils import concordance_index

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.phenoage import calculate_phenoage
from scripts.nhanes_real.download import CYCLES, RAW_DIR, MANIFEST_PATH

RESULTS_JSON_PATH = REPO_ROOT / "data" / "results" / "nhanes_real_results.json"
PLOT_PATH = REPO_ROOT / "docs" / "nhanes_real_validation.png"
REPORT_MD_PATH = REPO_ROOT / "docs" / "NHANES_REAL_VALIDATION.md"

# Official top-coding rules verified from CDC DEMO*.htm codebooks:
# 1999-2006 (DEMO..DEMO_D): individuals >= 85 are top-coded at 85 (exact range 0..84)
# 2007-2010 (DEMO_E..DEMO_F): individuals >= 80 are top-coded at 80 (exact range 0..79)
AGE_MAX_BY_CYCLE = {
    "1999_2000": 84,
    "2001_2002": 84,
    "2003_2004": 84,
    "2005_2006": 84,
    "2007_2008": 79,
    "2009_2010": 79,
}

# Unit conversion table from NHANES codebook units -> backend/app/core/phenoage.py canonical units
UNIT_CONVERSIONS = [
    {
        "nhanes_var": "LBXSAL",
        "phenoage_key": "albumin",
        "source_unit": "g/dL",
        "target_unit": "g/L",
        "formula": "LBXSAL * 10.0",
        "notes": "Consistent across all 6 cycles (1999-2010)",
    },
    {
        "nhanes_var": "LBXSCR (1999-2000, 2003-2010) / LBDSCR (2001-2002 L40_B)",
        "phenoage_key": "creatinine",
        "source_unit": "mg/dL",
        "target_unit": "umol/L",
        "formula": "LBXSCR * 88.4",
        "notes": "Standard molecular-weight factor (matches backend/app/core/normalizer.py)",
    },
    {
        "nhanes_var": "LBXSGL",
        "phenoage_key": "glucose",
        "source_unit": "mg/dL",
        "target_unit": "mmol/L",
        "formula": "LBXSGL / 18.0182",
        "notes": "Biochemistry-profile serum glucose (full MEC examined sample; includes non-fasted)",
    },
    {
        "nhanes_var": "LBXCRP",
        "phenoage_key": "crp",
        "source_unit": "mg/dL",
        "target_unit": "mg/dL",
        "formula": "LBXCRP * 1.0",
        "notes": "NHANES 1999-2010 LBXCRP is already reported in mg/dL per codebooks (no /10 scaling)",
    },
    {
        "nhanes_var": "LBXLYPCT",
        "phenoage_key": "lymphocyte_pct",
        "source_unit": "%",
        "target_unit": "%",
        "formula": "LBXLYPCT * 1.0",
        "notes": "CBC automated differential",
    },
    {
        "nhanes_var": "LBXMCVSI",
        "phenoage_key": "mcv",
        "source_unit": "fL",
        "target_unit": "fL",
        "formula": "LBXMCVSI * 1.0",
        "notes": "CBC mean cell volume",
    },
    {
        "nhanes_var": "LBXRDW",
        "phenoage_key": "rdw",
        "source_unit": "%",
        "target_unit": "%",
        "formula": "LBXRDW * 1.0",
        "notes": "CBC red cell distribution width",
    },
    {
        "nhanes_var": "LBXSAPSI (1999-2000, 2003-2010) / LBDSAPSI (2001-2002 L40_B)",
        "phenoage_key": "alp",
        "source_unit": "U/L",
        "target_unit": "U/L",
        "formula": "LBXSAPSI * 1.0",
        "notes": "Biochemistry-profile alkaline phosphatase",
    },
    {
        "nhanes_var": "LBXWBCSI",
        "phenoage_key": "wbc",
        "source_unit": "1000 cells/uL",
        "target_unit": "10^9/L",
        "formula": "LBXWBCSI * 1.0",
        "notes": "1000 cells/uL is numerically 1:1 equivalent to 10^9/L",
    },
]

PHENOAGE_BIOMARKER_COLS = [
    "albumin",
    "creatinine",
    "glucose",
    "crp",
    "lymphocyte_pct",
    "mcv",
    "rdw",
    "alp",
    "wbc",
]


def _load_cycle(cycle_cfg: Dict[str, str]) -> pd.DataFrame:
    cname = cycle_cfg["cycle"]
    cdir = RAW_DIR / cname

    demo_path = cdir / cycle_cfg["demo"].rsplit("/", 1)[-1]
    cbc_path = cdir / cycle_cfg["cbc"].rsplit("/", 1)[-1]
    biopro_path = cdir / cycle_cfg["biopro"].rsplit("/", 1)[-1]
    crp_path = cdir / cycle_cfg["crp"].rsplit("/", 1)[-1]
    mort_path = cdir / cycle_cfg["mortality"].rsplit("/", 1)[-1]

    for p in [demo_path, cbc_path, biopro_path, crp_path, mort_path]:
        if not p.exists():
            raise FileNotFoundError(
                f"Missing raw file {p}. Run `python backend/scripts/nhanes_real/download.py` first."
            )

    demo = pd.read_sas(demo_path, format="xport")[["SEQN", "RIDAGEYR", "RIAGENDR"]].copy()
    cbc = pd.read_sas(cbc_path, format="xport")[
        ["SEQN", "LBXWBCSI", "LBXLYPCT", "LBXMCVSI", "LBXRDW"]
    ].copy()

    biopro_raw = pd.read_sas(biopro_path, format="xport")
    # 2001-2002 L40_B names creatinine LBDSCR and alkaline phosphatase LBDSAPSI
    if "LBDSCR" in biopro_raw.columns and "LBXSCR" not in biopro_raw.columns:
        biopro_raw["LBXSCR"] = biopro_raw["LBDSCR"]
    if "LBDSAPSI" in biopro_raw.columns and "LBXSAPSI" not in biopro_raw.columns:
        biopro_raw["LBXSAPSI"] = biopro_raw["LBDSAPSI"]
    biopro = biopro_raw[["SEQN", "LBXSAL", "LBXSCR", "LBXSGL", "LBXSAPSI"]].copy()

    crp = pd.read_sas(crp_path, format="xport")[["SEQN", "LBXCRP"]].copy()

    # Official NCHS R_ReadInProgramAllSurveys.R fixed-width column layout (1-based -> 0-based):
    # seqn: 1-6 -> (0, 6); eligstat: 15 -> (14, 15); mortstat: 16 -> (15, 16); permth_exm: 46-48 -> (45, 48)
    mort = pd.read_fwf(
        mort_path,
        colspecs=[(0, 6), (14, 15), (15, 16), (45, 48)],
        names=["SEQN", "ELIGSTAT", "MORTSTAT", "PERMTH_EXM"],
        na_values=["", "."],
    )

    for frame in [demo, cbc, biopro, crp, mort]:
        frame["SEQN"] = pd.to_numeric(frame["SEQN"], errors="coerce").astype("Int64")

    merged = (
        demo.merge(mort, on="SEQN", how="left")
        .merge(biopro, on="SEQN", how="left")
        .merge(cbc, on="SEQN", how="left")
        .merge(crp, on="SEQN", how="left")
    )
    merged["cycle"] = cname
    merged["age_max_untopcoded"] = AGE_MAX_BY_CYCLE[cname]
    return merged


def build_and_analyze() -> Dict[str, Any]:
    print("=" * 72)
    print("REAL CDC NHANES (1999-2010) & NCHS 2019 MORTALITY REPLICATION")
    print("=" * 72)

    cycles_df = [_load_cycle(c) for c in CYCLES]
    raw_df = pd.concat(cycles_df, ignore_index=True)

    # Fix SAS XPORT zero-encoding underflow (< 1e-70 represents exact 0.0) on RIDAGEYR
    raw_df.loc[raw_df["RIDAGEYR"].abs() < 1e-10, "RIDAGEYR"] = 0.0

    # Unit conversions -> exact phenoage.py canonical units
    raw_df["albumin"] = raw_df["LBXSAL"] * 10.0          # g/dL -> g/L
    raw_df["creatinine"] = raw_df["LBXSCR"] * 88.4       # mg/dL -> umol/L
    raw_df["glucose"] = raw_df["LBXSGL"] / 18.0182       # mg/dL -> mmol/L
    raw_df["crp"] = raw_df["LBXCRP"] * 1.0               # already mg/dL
    raw_df["lymphocyte_pct"] = raw_df["LBXLYPCT"] * 1.0  # %
    raw_df["mcv"] = raw_df["LBXMCVSI"] * 1.0             # fL
    raw_df["rdw"] = raw_df["LBXRDW"] * 1.0               # %
    raw_df["alp"] = raw_df["LBXSAPSI"] * 1.0             # U/L
    raw_df["wbc"] = raw_df["LBXWBCSI"] * 1.0             # 1000 cells/uL == 10^9/L

    # Step-by-step N flow table
    n_flow: List[Dict[str, Any]] = []
    n_total = len(raw_df)
    n_flow.append({
        "step": "1. Total participants in NHANES 1999-2010 Demographics (DEMO*)",
        "remaining_n": int(n_total),
        "excluded_n": 0,
    })

    # Step 2: Adults 20-84 excluding cycle-specific top-coded ages
    adult_mask = (raw_df["RIDAGEYR"] >= 20) & (raw_df["RIDAGEYR"] <= raw_df["age_max_untopcoded"])
    df_adults = raw_df[adult_mask].copy()
    n_flow.append({
        "step": "2. Adults aged 20-84 excluding top-coded ages (>=85 in 1999-2006; >=80 in 2007-2010)",
        "remaining_n": int(len(df_adults)),
        "excluded_n": int(n_total - len(df_adults)),
    })

    # Step 3: Mortality linkage eligible (ELIGSTAT == 1) and non-missing MORTSTAT & PERMTH_EXM >= 0
    elig_mask = (
        (df_adults["ELIGSTAT"] == 1)
        & df_adults["MORTSTAT"].isin([0, 1])
        & df_adults["PERMTH_EXM"].notna()
        & (df_adults["PERMTH_EXM"] >= 0)
    )
    df_elig = df_adults[elig_mask].copy()
    n_flow.append({
        "step": "3. Mortality-eligible (ELIGSTAT == 1) with non-missing MORTSTAT and PERMTH_EXM >= 0",
        "remaining_n": int(len(df_elig)),
        "excluded_n": int(len(df_adults) - len(df_elig)),
    })

    # Step 4: Complete cases for all 9 PhenoAge biomarkers
    complete_mask = df_elig[PHENOAGE_BIOMARKER_COLS].notna().all(axis=1)
    df_final = df_elig[complete_mask].copy()
    n_flow.append({
        "step": "4. Complete cases across all 9 PhenoAge biomarkers (final analytic sample)",
        "remaining_n": int(len(df_final)),
        "excluded_n": int(len(df_elig) - len(df_final)),
    })

    print("\n--- Participant Exclusion N Flow ---")
    for row in n_flow:
        print(f"  {row['step']}: N = {row['remaining_n']:,} (excluded {row['excluded_n']:,})")

    # Step 5: Compute PhenoAge by IMPORTING calculate_phenoage from app.core.phenoage
    print("\nComputing PhenoAge via app.core.phenoage.calculate_phenoage...")
    phenoages: List[float] = []
    accels: List[float] = []
    mort_scores: List[float] = []

    records = df_final[PHENOAGE_BIOMARKER_COLS + ["RIDAGEYR"]].to_dict(orient="records")
    for rec in records:
        bio_input = {k: float(rec[k]) for k in PHENOAGE_BIOMARKER_COLS}
        res = calculate_phenoage(bio_input, float(rec["RIDAGEYR"]))
        if not res["is_valid"] or res["phenoage"] is None:
            raise RuntimeError(f"Unexpected invalid PhenoAge on complete-case row: {res}")
        phenoages.append(float(res["phenoage"]))
        accels.append(float(res["age_acceleration"]))
        mort_scores.append(float(res["mortality_score_10yr"]))

    df_final["phenoage"] = phenoages
    df_final["age_acceleration"] = accels
    df_final["mortality_score_10yr"] = mort_scores
    df_final["MORTSTAT"] = df_final["MORTSTAT"].astype(int)
    df_final["PERMTH_EXM"] = df_final["PERMTH_EXM"].astype(float)

    # Pearson r between PhenoAge and chronological age
    pearson_r, pearson_p = stats.pearsonr(df_final["RIDAGEYR"], df_final["phenoage"])

    # Cox PH adjusted for chronological age via lifelines
    cox_df = df_final[["PERMTH_EXM", "MORTSTAT", "age_acceleration", "RIDAGEYR"]].copy()
    cph = CoxPHFitter()
    cph.fit(cox_df, duration_col="PERMTH_EXM", event_col="MORTSTAT")

    hr_accel = float(np.exp(cph.params_["age_acceleration"]))
    ci_df = cph.confidence_intervals_
    hr_ci_low = float(np.exp(ci_df.loc["age_acceleration", "95% lower-bound"]))
    hr_ci_high = float(np.exp(ci_df.loc["age_acceleration", "95% upper-bound"]))
    hr_p = float(cph.summary.loc["age_acceleration", "p"])

    hr_age = float(np.exp(cph.params_["RIDAGEYR"]))
    hr_age_ci_low = float(np.exp(ci_df.loc["RIDAGEYR", "95% lower-bound"]))
    hr_age_ci_high = float(np.exp(ci_df.loc["RIDAGEYR", "95% upper-bound"]))

    # C-index: PhenoAge alone vs chronological age alone (both direct concordance_index and univariate Cox)
    c_index_phenoage = float(
        concordance_index(df_final["PERMTH_EXM"], -df_final["phenoage"], df_final["MORTSTAT"])
    )
    c_index_chrono_age = float(
        concordance_index(df_final["PERMTH_EXM"], -df_final["RIDAGEYR"], df_final["MORTSTAT"])
    )

    # 10-year mortality & full follow-up mortality by PhenoAge acceleration quartile
    df_final["accel_quartile"] = pd.qcut(
        df_final["age_acceleration"],
        q=4,
        labels=["Q1 (Lowest)", "Q2", "Q3", "Q4 (Highest)"],
    )

    # Censor at 120 months for explicit 10-year Cox/KM mortality analysis
    df_final["event_10yr"] = np.where((df_final["MORTSTAT"] == 1) & (df_final["PERMTH_EXM"] <= 120.0), 1, 0)
    df_final["time_10yr"] = np.minimum(df_final["PERMTH_EXM"], 120.0)

    quartiles_summary: List[Dict[str, Any]] = []
    q1_km_rate = None
    for q_label, grp in df_final.groupby("accel_quartile", observed=True):
        kmf = KaplanMeierFitter()
        kmf.fit(grp["time_10yr"], event_observed=grp["event_10yr"])
        # Survival at 120 months (or max available time if <=120)
        t_eval = min(120.0, float(grp["time_10yr"].max()))
        surv_10yr = float(kmf.predict(t_eval))
        km_mort_10yr_pct = (1.0 - surv_10yr) * 100.0

        deaths_10yr = int(grp["event_10yr"].sum())
        crude_10yr_pct = (deaths_10yr / len(grp)) * 100.0

        deaths_all = int(grp["MORTSTAT"].sum())
        all_followup_pct = (deaths_all / len(grp)) * 100.0

        if q1_km_rate is None:
            q1_km_rate = km_mort_10yr_pct if km_mort_10yr_pct > 0 else 1.0

        quartiles_summary.append({
            "quartile": str(q_label),
            "n": int(len(grp)),
            "accel_min": round(float(grp["age_acceleration"].min()), 1),
            "accel_max": round(float(grp["age_acceleration"].max()), 1),
            "mean_accel": round(float(grp["age_acceleration"].mean()), 2),
            "mean_age": round(float(grp["RIDAGEYR"].mean()), 1),
            "mean_phenoage": round(float(grp["phenoage"].mean()), 1),
            "deaths_10yr": deaths_10yr,
            "crude_10yr_mortality_pct": round(crude_10yr_pct, 2),
            "km_10yr_mortality_pct": round(km_mort_10yr_pct, 2),
            "km_rr_vs_q1": round(km_mort_10yr_pct / q1_km_rate, 2),
            "deaths_total_followup": deaths_all,
            "total_followup_mortality_pct": round(all_followup_pct, 2),
        })

    # Cycle breakdown summary
    cycle_counts = (
        df_final.groupby("cycle")
        .agg(
            n=("SEQN", "count"),
            deaths_all=("MORTSTAT", "sum"),
            deaths_10yr=("event_10yr", "sum"),
            median_followup_months=("PERMTH_EXM", "median"),
            mean_age=("RIDAGEYR", "mean"),
            mean_phenoage=("phenoage", "mean"),
        )
        .reset_index()
        .to_dict(orient="records")
    )
    for cc in cycle_counts:
        cc["n"] = int(cc["n"])
        cc["deaths_all"] = int(cc["deaths_all"])
        cc["deaths_10yr"] = int(cc["deaths_10yr"])
        cc["median_followup_months"] = round(float(cc["median_followup_months"]), 1)
        cc["mean_age"] = round(float(cc["mean_age"]), 1)
        cc["mean_phenoage"] = round(float(cc["mean_phenoage"]), 1)

    # Load URLs from download manifest if available
    source_urls: List[str] = []
    if MANIFEST_PATH.exists():
        manifest_data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        source_urls = [item["url"] for item in manifest_data.get("files", [])]

    results: Dict[str, Any] = {
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "dataset": "CDC NHANES 1999-2010 (6 cycles) + NCHS 2019 Public-Use Linked Mortality Files",
        "weighted": False,
        "glucose_definition": "Standard biochemistry profile serum glucose (LBXSGL, full MEC sample, includes non-fasted)",
        "n_flow": n_flow,
        "analytic_n": int(len(df_final)),
        "total_deaths_all_followup": int(df_final["MORTSTAT"].sum()),
        "deaths_within_10yr": int(df_final["event_10yr"].sum()),
        "median_followup_months": round(float(df_final["PERMTH_EXM"].median()), 1),
        "max_followup_months": round(float(df_final["PERMTH_EXM"].max()), 1),
        "mean_chronological_age": round(float(df_final["RIDAGEYR"].mean()), 2),
        "mean_phenoage": round(float(df_final["phenoage"].mean()), 2),
        "mean_age_acceleration": round(float(df_final["age_acceleration"].mean()), 2),
        "pearson_r_phenoage_vs_age": round(float(pearson_r), 4),
        "pearson_p_value": float(pearson_p),
        "cox_ph_adjusted_for_age": {
            "hr_per_1yr_age_acceleration": round(hr_accel, 4),
            "hr_95_ci": [round(hr_ci_low, 4), round(hr_ci_high, 4)],
            "p_value": hr_p,
            "hr_per_1yr_chronological_age": round(hr_age, 4),
            "age_hr_95_ci": [round(hr_age_ci_low, 4), round(hr_age_ci_high, 4)],
            "joint_model_c_index": round(float(cph.concordance_index_), 4),
        },
        "c_index_comparison": {
            "phenoage_alone": round(c_index_phenoage, 4),
            "chronological_age_alone": round(c_index_chrono_age, 4),
            "delta_c_index": round(c_index_phenoage - c_index_chrono_age, 4),
        },
        "quartiles_by_age_acceleration": quartiles_summary,
        "by_cycle": cycle_counts,
        "source_urls": source_urls,
    }

    RESULTS_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    RESULTS_JSON_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nSaved JSON results to {RESULTS_JSON_PATH}")

    _render_plot(df_final, quartiles_summary, results, PLOT_PATH)
    print(f"Saved plot to {PLOT_PATH}")

    _write_markdown_report(results, REPORT_MD_PATH)
    print(f"Saved report to {REPORT_MD_PATH}")

    print("\n=== REAL NHANES REPLICATION SUMMARY ===")
    print(f"Analytic N: {results['analytic_n']:,}")
    print(f"Total deaths (through Dec 2019): {results['total_deaths_all_followup']:,} | <=120m deaths: {results['deaths_within_10yr']:,}")
    print(f"Pearson r (PhenoAge vs Age): {results['pearson_r_phenoage_vs_age']:.4f}")
    print(
        f"Adjusted Cox HR per +1 yr Age Acceleration: {hr_accel:.4f} "
        f"(95% CI: {hr_ci_low:.4f} - {hr_ci_high:.4f}, p = {hr_p:.2e})"
    )
    print(
        f"C-index: PhenoAge = {c_index_phenoage:.4f} vs Age alone = {c_index_chrono_age:.4f} "
        f"(delta = {c_index_phenoage - c_index_chrono_age:+.4f})"
    )
    for q in quartiles_summary:
        print(
            f"  {q['quartile']}: N={q['n']:,}, 10-yr KM mort={q['km_10yr_mortality_pct']:.2f}% "
            f"(RR={q['km_rr_vs_q1']:.2f}x), crude 10-yr={q['crude_10yr_mortality_pct']:.2f}%"
        )

    return results


def _render_plot(
    df_final: pd.DataFrame,
    quartiles_summary: List[Dict[str, Any]],
    results: Dict[str, Any],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Panel A: PhenoAge vs Chronological Age (random subset for clean scatter rendering)
    sub = df_final.sample(n=min(4000, len(df_final)), random_state=42)
    ax1.scatter(sub["RIDAGEYR"], sub["phenoage"], alpha=0.18, color="#1e40af", s=12, edgecolors="none")

    x_min, x_max = 18.0, 86.0
    ax1.plot([x_min, x_max], [x_min, x_max], "k--", lw=1.4, label="Identity (PhenoAge = Age)")

    slope, intercept, _, _, _ = stats.linregress(df_final["RIDAGEYR"], df_final["phenoage"])
    xs = np.linspace(x_min, x_max, 100)
    r_val = results["pearson_r_phenoage_vs_age"]
    ax1.plot(xs, intercept + slope * xs, color="#dc2626", lw=2, label=f"OLS Fit (r = {r_val:.3f})")

    ax1.set_xlim(x_min, x_max)
    ax1.set_ylim(0, min(135.0, float(np.percentile(df_final["phenoage"], 99.8)) + 15.0))
    ax1.set_title("A. PhenoAge vs. Chronological Age (Real NHANES 1999-2010)", fontsize=10.5, fontweight="bold")
    ax1.set_xlabel("Chronological Age at Screening (years)", fontsize=9.5)
    ax1.set_ylabel("Computed PhenoAge (years)", fontsize=9.5)
    ax1.grid(True, linestyle=":", alpha=0.6)
    ax1.legend(loc="upper left", frameon=True, fontsize=8.5)
    ax1.text(
        0.04, 0.72,
        f"N = {results['analytic_n']:,} (unweighted)\nPearson r = {r_val:.4f}\nC-index: PhenoAge {results['c_index_comparison']['phenoage_alone']:.3f} vs Age {results['c_index_comparison']['chronological_age_alone']:.3f}",
        transform=ax1.transAxes,
        fontsize=8.2,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8fafc", edgecolor="#cbd5e1"),
    )

    # Panel B: 10-Year Kaplan-Meier All-Cause Mortality by Age Acceleration Quartile
    labels = [q["quartile"] for q in quartiles_summary]
    km_rates = [q["km_10yr_mortality_pct"] for q in quartiles_summary]
    colors = ["#22c55e", "#3b82f6", "#f59e0b", "#ef4444"]

    bars = ax2.bar(labels, km_rates, color=colors, width=0.55, edgecolor="#334155", linewidth=0.9)
    ax2.set_title("B. 10-Year KM All-Cause Mortality by Age Acceleration Quartile", fontsize=10.5, fontweight="bold")
    ax2.set_ylabel("10-Year Kaplan-Meier Mortality (%)", fontsize=9.5)
    ax2.set_ylim(0, max(km_rates) * 1.32)
    ax2.grid(axis="y", linestyle=":", alpha=0.6)

    for bar, rate, q in zip(bars, km_rates, quartiles_summary):
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + max(km_rates) * 0.025,
            f"{rate:.2f}%\n({q['km_rr_vs_q1']:.2f}x)",
            ha="center",
            va="bottom",
            fontsize=8.5,
            fontweight="bold",
        )

    cox = results["cox_ph_adjusted_for_age"]
    p_str = "< 0.0001" if cox["p_value"] < 1e-4 else f"= {cox['p_value']:.2e}"
    ax2.text(
        0.04, 0.78,
        f"Age-Adjusted Cox PH (NCHS 2019 LMF):\nHR per +1 yr Accel = {cox['hr_per_1yr_age_acceleration']:.3f} "
        f"(95% CI: {cox['hr_95_ci'][0]:.3f}-{cox['hr_95_ci'][1]:.3f})\np {p_str}",
        transform=ax2.transAxes,
        fontsize=8.2,
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#f8fafc", edgecolor="#cbd5e1"),
    )

    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()


def _write_markdown_report(results: Dict[str, Any], md_path: Path) -> None:
    cox = results["cox_ph_adjusted_for_age"]
    cidx = results["c_index_comparison"]

    lines = [
        "# Real CDC NHANES (1999–2010) & NCHS 2019 Linked Mortality Replication",
        "",
        f"> **Generated:** `{results['generated_at_utc']}`",
        f"> **Script:** [`backend/scripts/nhanes_real/build_cohort.py`](../backend/scripts/nhanes_real/build_cohort.py) (uses `calculate_phenoage` imported directly from [`backend/app/core/phenoage.py`](../backend/app/core/phenoage.py))",
        f"> **Raw Data JSON Output:** [`data/results/nhanes_real_results.json`](../data/results/nhanes_real_results.json)",
        "",
        "---",
        "",
        "## 1. Cohort & Participant Exclusion Flow",
        "",
        "| Exclusion Step | Remaining $N$ | Excluded $N$ |",
        "| :--- | ---: | ---: |",
    ]
    for row in results["n_flow"]:
        lines.append(f"| {row['step']} | {row['remaining_n']:,} | {row['excluded_n']:,} |")

    lines.extend([
        "",
        f"- **Final Analytic Cohort:** **{results['analytic_n']:,} adults** across 6 cycles (1999–2000 through 2009–2010).",
        f"- **Follow-Up (PERMTH_EXM):** Median **{results['median_followup_months']} months** (max {results['max_followup_months']} months through Dec 31, 2019).",
        f"- **Mortality Events (`MORTSTAT == 1`):** **{results['total_deaths_all_followup']:,}** across full follow-up (**{results['deaths_within_10yr']:,}** within $\\le 120$ months).",
        "",
        "---",
        "",
        "## 2. Primary Survival & Concordance Results (Unweighted)",
        "",
        f"- **Cox Proportional Hazards (`lifelines.CoxPHFitter`, adjusted for `RIDAGEYR`):**",
        f"  - **HR per +1 year of PhenoAge Acceleration (`PhenoAge - Age`):** **{cox['hr_per_1yr_age_acceleration']:.4f}** (95% CI: **{cox['hr_95_ci'][0]:.4f}–{cox['hr_95_ci'][1]:.4f}**, $p = {cox['p_value']:.2e}$)",
        f"  - **HR per +1 year of Chronological Age (`RIDAGEYR`):** {cox['hr_per_1yr_chronological_age']:.4f} (95% CI: {cox['age_hr_95_ci'][0]:.4f}–{cox['age_hr_95_ci'][1]:.4f})",
        "- **Concordance Index (c-index) Comparison:**",
        f"  - **PhenoAge alone:** **{cidx['phenoage_alone']:.4f}**",
        f"  - **Chronological Age alone:** **{cidx['chronological_age_alone']:.4f}**",
        f"  - **Delta (PhenoAge - Age):** **{cidx['delta_c_index']:+.4f}**",
        f"- **Pearson Correlation (PhenoAge vs. Chronological Age):** **$r = {results['pearson_r_phenoage_vs_age']:.4f}$** ($p = {results['pearson_p_value']:.2e}$)",
        "",
        "### 10-Year & Full Follow-Up Mortality by Age Acceleration Quartile",
        "",
        "| Quartile | Accel Range (yrs) | Mean Accel | $N$ | $\\le 120$m Deaths | Crude 10-Yr Mort (%) | KM 10-Yr Mort (%) | KM RR vs Q1 | Full Follow-Up Mort (%) |",
        "| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])

    for q in results["quartiles_by_age_acceleration"]:
        lines.append(
            f"| **{q['quartile']}** | {q['accel_min']:+.1f} to {q['accel_max']:+.1f} | {q['mean_accel']:+.2f} | "
            f"{q['n']:,} | {q['deaths_10yr']:,} | {q['crude_10yr_mortality_pct']:.2f}% | "
            f"**{q['km_10yr_mortality_pct']:.2f}%** | {q['km_rr_vs_q1']:.2f}x | {q['total_followup_mortality_pct']:.2f}% |"
        )

    lines.extend([
        "",
        "![Real NHANES Validation Plot](./nhanes_real_validation.png)",
        "",
        "---",
        "",
        "## 3. Variable Mapping, Unit Conversions & Glucose Choice",
        "",
        "### Glucose Variable Rationale (`BIOPRO` `LBXSGL` vs. `GLU` Fasting)",
        "We use **standard biochemistry profile serum glucose (`LBXSGL`)** rather than the fasting plasma glucose subsample (`GLU_*` / `LBXGLU`). In NHANES 1999–2010, fasting plasma glucose is collected only in the morning fasting subsample (~half of MEC participants), whereas `BIOPRO` (`LBXSGL`) is measured across the full examined adult cohort aged 12+ and matches the biomarker definition used in the Levine et al. (2018) NHANES IV validation cohort. Note that `LBXSGL` includes non-fasted participants.",
        "",
        "### NHANES Variable & Unit Conversions",
        "",
        "| NHANES Variable | PhenoAge Key | Source Unit | Target Unit (`phenoage.py`) | Conversion | Notes |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])
    for conv in UNIT_CONVERSIONS:
        lines.append(
            f"| `{conv['nhanes_var']}` | `{conv['phenoage_key']}` | {conv['source_unit']} | {conv['target_unit']} | `{conv['formula']}` | {conv['notes']} |"
        )

    lines.extend([
        "",
        "### Cycle-Specific Breakdown & Age Top-Coding",
        "Per official CDC `DEMO*.htm` codebooks, `RIDAGEYR` is top-coded at **85** in 1999–2006 (`>=85` collapsed to 85; `20–84` un-topcoded) and at **80** in 2007–2010 (`>=80` collapsed to 80; `20–79` un-topcoded). Top-coded ages are excluded.",
        "",
        "| Cycle | Analytic $N$ | Mean Age | Mean PhenoAge | Median Follow-Up (mo) | $\\le 120$m Deaths | Full Follow-Up Deaths |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for cc in results["by_cycle"]:
        lines.append(
            f"| `{cc['cycle']}` | {cc['n']:,} | {cc['mean_age']} | {cc['mean_phenoage']} | {cc['median_followup_months']} | {cc['deaths_10yr']:,} | {cc['deaths_all']:,} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Limitations",
        "",
        "1. **US Population:** NHANES is a US civilian non-institutionalized population survey. Biomarker distributions, baseline mortality rates, and cardiometabolic risk relationships differ in Indian / South Asian populations.",
        "2. **Unweighted Analysis:** Results above are unweighted NHANES sample estimates (survey weights, strata, and PSUs were not applied), so hazard ratios and percentages reflect the analytic sample rather than weighted US national population rates.",
        "3. **Non-Fasting Biochemistry-Profile Glucose (`LBXSGL`):** Using standard biochemistry-profile serum glucose instead of fasting plasma glucose maximizes sample size across all MEC adults but includes participants who were not fasting at blood draw.",
        "4. **Public-Use Linked Mortality Perturbation:** Per NCHS disclosure-avoidance rules, the public-use 2019 Linked Mortality Files apply perturbation to follow-up times and/or vital status for a small subset of records to protect participant privacy; therefore, estimates may differ slightly from NCHS restricted-use linked mortality files.",
        "",
        "---",
        "",
        "## 5. Official Data Sources Downloaded (`data/nhanes_raw/download_manifest.json`)",
        "",
    ])
    for u in results.get("source_urls", []):
        lines.append(f"- `{u}`")

    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    build_and_analyze()
