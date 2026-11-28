import io
import json
from pathlib import Path
import pandas as pd


def test_age_topcoding_rules_and_unit_conversions():
    from scripts.nhanes_real.build_cohort import AGE_MAX_BY_CYCLE, UNIT_CONVERSIONS

    # 1999-2006 cycles top-code at 85 (un-topcoded max = 84); 2007-2010 top-code at 80 (un-topcoded max = 79)
    assert AGE_MAX_BY_CYCLE["1999_2000"] == 84
    assert AGE_MAX_BY_CYCLE["2005_2006"] == 84
    assert AGE_MAX_BY_CYCLE["2007_2008"] == 79
    assert AGE_MAX_BY_CYCLE["2009_2010"] == 79

    conv_map = {c["phenoage_key"]: c for c in UNIT_CONVERSIONS}
    assert set(conv_map.keys()) == {
        "albumin", "creatinine", "glucose", "crp", "lymphocyte_pct", "mcv", "rdw", "alp", "wbc"
    }
    assert conv_map["crp"]["source_unit"] == "mg/dL"
    assert conv_map["crp"]["target_unit"] == "mg/dL"


def test_nchs_fixed_width_parser_layout():
    # Official NCHS R_ReadInProgramAllSurveys.R columns:
    # seqn=(0,6), eligstat=(14,15), mortstat=(15,16), permth_exm=(45,48)
    line_eligible = "    12        10 10  0000                    120\n"
    line_inelig = "    13        2. .   0000                       \n"
    df = pd.read_fwf(
        io.StringIO(line_eligible + line_inelig),
        colspecs=[(0, 6), (14, 15), (15, 16), (45, 48)],
        names=["SEQN", "ELIGSTAT", "MORTSTAT", "PERMTH_EXM"],
        na_values=["", "."],
    )
    assert int(df.loc[0, "SEQN"]) == 12
    assert int(df.loc[0, "ELIGSTAT"]) == 1
    assert int(df.loc[0, "MORTSTAT"]) == 0
    assert int(df.loc[0, "PERMTH_EXM"]) == 120
    assert int(df.loc[1, "ELIGSTAT"]) == 2
    assert pd.isna(df.loc[1, "MORTSTAT"])


def test_real_nhanes_results_json_exists_and_consistent():
    results_path = Path(__file__).resolve().parent.parent.parent / "data" / "results" / "nhanes_real_results.json"
    assert results_path.exists()
    data = json.loads(results_path.read_text(encoding="utf-8"))
    assert data["weighted"] is False
    assert data["analytic_n"] > 20000
    assert len(data["n_flow"]) == 4
    assert len(data["quartiles_by_age_acceleration"]) == 4
    assert "hr_per_1yr_age_acceleration" in data["cox_ph_adjusted_for_age"]
    assert "joint_model_c_index_6dp" in data["cox_ph_adjusted_for_age"]
    assert "phenoage_alone" in data["c_index_comparison"]
    assert "phenoage_alone_6dp" in data["c_index_comparison"]

    sens = data.get("sensitivity_analyses")
    assert sens is not None
    assert sens["hr_per_1sd_age_acceleration"]["hr"] > 1.0
    assert sens["winsorized_1st_99th_percentile"]["per_1yr"]["hr"] > 1.0
    assert "joint_model_c_index_6dp" in sens["winsorized_1st_99th_percentile"]["per_1yr"]
    assert sens["excluding_crp_gt_10_mg_dl"]["excluded_n"] >= 0
    assert sens["residual_based_acceleration"]["per_1yr"]["hr"] == data["cox_ph_adjusted_for_age"]["hr_per_1yr_age_acceleration"]

    top20 = sens["top_20_extreme_acceleration_rows"]
    assert len(top20) == 20
    required_markers = {
        "albumin_g_l", "creatinine_umol_l", "glucose_mmol_l", "crp_mg_dl",
        "lymphocyte_pct", "mcv_fl", "rdw_pct", "alp_u_l", "wbc_10_9_l", "assessment"
    }
    for row in top20:
        assert required_markers.issubset(row.keys())
        assert "consistent_with_clinical_extreme" in row["assessment"]

