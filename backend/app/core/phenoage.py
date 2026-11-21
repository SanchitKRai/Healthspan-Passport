import math
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Core 9 PhenoAge required biomarker keys
PHENOAGE_REQUIRED_KEYS = [
    "albumin",        # g/L
    "creatinine",     # µmol/L
    "glucose",        # mmol/L (or glucose_fasting)
    "crp",            # mg/dL
    "lymphocyte_pct", # %
    "mcv",            # fL
    "rdw",            # %
    "alp",            # U/L
    "wbc",            # 10^9/L (or 10^3/µL)
]

# Published Levine et al. (2018) Model Coefficients
LEVINE_INTERCEPT = -19.907
COEFFICIENTS = {
    "albumin": -0.0336,
    "creatinine": 0.0095,
    "glucose": 0.1953,
    "crp": 0.0954,
    "lymphocyte_pct": -0.0120,
    "mcv": 0.0268,
    "rdw": 0.3306,
    "alp": 0.00188,
    "wbc": 0.0554,
    "age": 0.0804,
}

# Gompertz model parameters (120 months = 10 years mortality)
GOMPERTZ_GAMMA = 0.0076927
TIME_HORIZON_MONTHS = 120.0
# (exp(120 * gamma) - 1) / gamma
GOMPERTZ_FACTOR = (math.exp(TIME_HORIZON_MONTHS * GOMPERTZ_GAMMA) - 1.0) / GOMPERTZ_GAMMA


def calculate_phenoage(
    biomarkers: Dict[str, Optional[float]],
    chronological_age: float
) -> Dict[str, Any]:
    """
    Implements the published Levine et al. (2018) PhenoAge biological age algorithm.
    Strict Rule: If any of the 9 required biomarkers is missing or null, returns phenoage=None
    and lists the missing markers. NEVER guesses or imputes missing values.
    """
    # Normalize key alias: 'glucose_fasting' -> 'glucose'
    clean_bio = dict(biomarkers)
    if "glucose_fasting" in clean_bio and "glucose" not in clean_bio:
        clean_bio["glucose"] = clean_bio["glucose_fasting"]

    missing = []
    for k in PHENOAGE_REQUIRED_KEYS:
        if clean_bio.get(k) is None:
            missing.append(k)

    if missing:
        return {
            "is_valid": False,
            "phenoage": None,
            "age_acceleration": None,
            "mortality_score_10yr": None,
            "missing_markers": missing,
            "message": f"Biological age cannot be computed because {len(missing)} required test(s) are missing ({', '.join(missing)}). Standard CBC differential and hs-CRP are needed."
        }

    try:
        # Linear Combination (xb)
        crp_val = max(0.001, float(clean_bio["crp"]))  # Numerical floor for ln(CRP)
        ln_crp = math.log(crp_val)

        xb = (
            LEVINE_INTERCEPT
            + COEFFICIENTS["albumin"] * float(clean_bio["albumin"])
            + COEFFICIENTS["creatinine"] * float(clean_bio["creatinine"])
            + COEFFICIENTS["glucose"] * float(clean_bio["glucose"])
            + COEFFICIENTS["crp"] * ln_crp
            + COEFFICIENTS["lymphocyte_pct"] * float(clean_bio["lymphocyte_pct"])
            + COEFFICIENTS["mcv"] * float(clean_bio["mcv"])
            + COEFFICIENTS["rdw"] * float(clean_bio["rdw"])
            + COEFFICIENTS["alp"] * float(clean_bio["alp"])
            + COEFFICIENTS["wbc"] * float(clean_bio["wbc"])
            + COEFFICIENTS["age"] * float(chronological_age)
        )

        # 10-year Mortality Risk Score (Gompertz proportional hazards)
        exp_xb = math.exp(xb)
        mortality_score = 1.0 - math.exp(-exp_xb * GOMPERTZ_FACTOR)
        mortality_score = max(1e-7, min(0.9999999, mortality_score))

        # Biological Age (PhenoAge in years)
        # Using algebraically stable formulation: -0.00553 * ln(1 - M) = 0.00553 * exp_xb * GOMPERTZ_FACTOR
        term = 0.00553 * exp_xb * GOMPERTZ_FACTOR
        phenoage = 141.50225 + (math.log(term) / 0.090165)

        age_acceleration = phenoage - chronological_age

        return {
            "is_valid": True,
            "phenoage": round(phenoage, 1),
            "age_acceleration": round(age_acceleration, 1),
            "mortality_score_10yr": round(mortality_score * 100, 2),  # percentage
            "missing_markers": [],
            "message": "PhenoAge successfully computed from routine CBC, metabolic markers, and chronological age."
        }
    except Exception as e:
        logger.error(f"Error computing PhenoAge: {e}")
        return {
            "is_valid": False,
            "phenoage": None,
            "age_acceleration": None,
            "mortality_score_10yr": None,
            "missing_markers": [],
            "message": f"Calculation error: {str(e)}"
        }


def evaluate_risk_flags(
    biomarkers: Dict[str, Optional[float]],
    sex: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    Evaluates multi-organ preventive health risk flags.
    Operates independently of whether CRP or PhenoAge is available.
    Wording is strictly educational and non-diagnostic.
    """
    flags = []
    is_male = (sex or "").lower().startswith("m")
    is_female = (sex or "").lower().startswith("f")

    # 1. Glycemic / Metabolic Risk
    glucose = biomarkers.get("glucose_fasting") or biomarkers.get("glucose")
    hba1c = biomarkers.get("hba1c")
    if glucose is not None or hba1c is not None:
        if (hba1c and hba1c >= 6.5) or (glucose and glucose >= 126.0):
            flags.append({
                "category": "glycemic",
                "title": "Glycemic Regulation (Elevated / Diabetic Range)",
                "status": "elevated",
                "markers": [f"Glucose: {glucose} mg/dL" if glucose else "", f"HbA1c: {hba1c}%" if hba1c else ""],
                "message": "Fasting blood sugar or HbA1c is in the elevated range. Recommend discussing with a clinician for structured blood sugar monitoring.",
                "recommendation": "Consult a physician, consider oral glucose tolerance confirmation, and maintain whole-grain, low-glycemic dietary habits."
            })
        elif (hba1c and hba1c >= 5.7) or (glucose and glucose >= 100.0):
            flags.append({
                "category": "glycemic",
                "title": "Early Glycemic Imbalance (Pre-Diabetes Range)",
                "status": "elevated",
                "markers": [f"Glucose: {glucose} mg/dL" if glucose else "", f"HbA1c: {hba1c}%" if hba1c else ""],
                "message": "Values suggest early impaired fasting glucose or borderline pre-diabetes. Early lifestyle and nutrition intervention is highly effective here.",
                "recommendation": "Increase daily post-meal walking, reduce refined carbohydrates and added sugars, and repeat fasting panel in 3 months."
            })
        else:
            flags.append({
                "category": "glycemic",
                "title": "Optimal Glycemic Regulation",
                "status": "optimal",
                "markers": [f"Glucose: {glucose} mg/dL" if glucose else ""],
                "message": "Fasting blood glucose is well within the healthy preventive interval.",
                "recommendation": "Maintain balanced dietary fiber and active lifestyle."
            })

    # 2. Cardiovascular & Lipid Risk
    chol = biomarkers.get("cholesterol_total")
    tg = biomarkers.get("triglycerides")
    ldl = biomarkers.get("cholesterol_ldl")
    hdl = biomarkers.get("cholesterol_hdl")
    if any(x is not None for x in [chol, tg, ldl, hdl]):
        elevated_items = []
        if tg and tg >= 150.0:
            elevated_items.append(f"Triglycerides {tg} mg/dL")
        if chol and chol >= 200.0:
            elevated_items.append(f"Total Cholesterol {chol} mg/dL")
        if ldl and ldl >= 130.0:
            elevated_items.append(f"LDL {ldl} mg/dL")
        if hdl and ((is_male and hdl < 40.0) or (is_female and hdl < 50.0)):
            elevated_items.append(f"Low HDL {hdl} mg/dL")

        if elevated_items:
            flags.append({
                "category": "cardiovascular_lipid",
                "title": "Lipid Profile (Elevated Cardiovascular Markers)",
                "status": "elevated",
                "markers": elevated_items,
                "message": f"Elevated lipid fractions noted ({', '.join(elevated_items)}). Elevated triglycerides with lower HDL is a common atherogenic pattern in South Asian populations.",
                "recommendation": "Incorporate omega-3 fatty acids (flaxseeds, walnuts), reduce trans/refined fats, and discuss cardiovascular risk assessment with a doctor."
            })
        else:
            flags.append({
                "category": "cardiovascular_lipid",
                "title": "Optimal Lipid Profile",
                "status": "optimal",
                "markers": [f"Cholesterol: {chol} mg/dL" if chol else ""],
                "message": "Circulating cholesterol and lipid levels are within optimal cardioprotective ranges.",
                "recommendation": "Continue heart-healthy diet with regular aerobic exercise."
            })

    # 3. Renal & Kidney Function
    creat = biomarkers.get("creatinine")
    bun = biomarkers.get("bun")
    uric = biomarkers.get("uric_acid")
    if creat is not None or bun is not None or uric is not None:
        renal_concerns = []
        creat_threshold = 1.3 if is_male else (1.1 if is_female else 1.2)
        if creat and creat > creat_threshold:
            renal_concerns.append(f"Creatinine {creat} mg/dL")
        if bun and bun > 22.0:
            renal_concerns.append(f"BUN/Urea {bun} mg/dL")
        if uric and uric > 7.2:
            renal_concerns.append(f"Uric Acid {uric} mg/dL")

        if renal_concerns:
            flags.append({
                "category": "renal",
                "title": "Renal Function Screen (Borderline Marker)",
                "status": "elevated",
                "markers": renal_concerns,
                "message": f"Mild elevation in renal filtration markers ({', '.join(renal_concerns)}). Can be influenced by hydration, protein intake, or physical exertion.",
                "recommendation": "Maintain adequate daily hydration (2.5-3L water) and have kidney function / eGFR re-checked by your physician."
            })
        else:
            flags.append({
                "category": "renal",
                "title": "Healthy Kidney Filtration",
                "status": "optimal",
                "markers": [f"Creatinine: {creat} mg/dL" if creat else ""],
                "message": "Serum creatinine and nitrogenous waste clearance indicators appear healthy.",
                "recommendation": "Continue normal hydration."
            })

    # 4. Hepatic / Liver Enzymes
    alt = biomarkers.get("alt_sgpt")
    ast = biomarkers.get("ast_sgot")
    bili = biomarkers.get("bilirubin_total")
    if alt is not None or ast is not None or bili is not None:
        liver_concerns = []
        if alt and alt > 56.0:
            liver_concerns.append(f"ALT/SGPT {alt} U/L")
        if ast and ast > 40.0:
            liver_concerns.append(f"AST/SGOT {ast} U/L")
        if bili and bili > 1.2:
            liver_concerns.append(f"Total Bilirubin {bili} mg/dL")

        if liver_concerns:
            flags.append({
                "category": "hepatic",
                "title": "Hepatic Enzyme Screen (Mild Elevation)",
                "status": "elevated",
                "markers": liver_concerns,
                "message": f"Elevated transaminases noted ({', '.join(liver_concerns)}). Mild elevations are commonly linked to metabolic fatty liver, medications, or alcohol intake.",
                "recommendation": "Review any hepatotoxic medications or supplements with your doctor and consider ultrasound screening for metabolic liver health."
            })
        else:
            flags.append({
                "category": "hepatic",
                "title": "Normal Hepatic Enzyme Profile",
                "status": "optimal",
                "markers": [f"ALT: {alt} U/L" if alt else ""],
                "message": "Liver transaminases and bilirubin values indicate healthy liver cell integrity.",
                "recommendation": "Maintain balanced antioxidant intake."
            })

    # 5. Hematologic / Anemia Screen
    hb = biomarkers.get("hemoglobin")
    mcv = biomarkers.get("mcv")
    rdw = biomarkers.get("rdw")
    if hb is not None:
        hb_threshold = 13.0 if is_male else (12.0 if is_female else 12.0)
        if hb < hb_threshold:
            anemia_type = "Microcytic (iron-deficiency pattern)" if mcv and mcv < 80.0 else "Borderline low hemoglobin"
            flags.append({
                "category": "hematologic",
                "title": f"Anemia Screening ({anemia_type})",
                "status": "elevated",
                "markers": [f"Hemoglobin: {hb} g/dL", f"MCV: {mcv} fL" if mcv else "", f"RDW: {rdw}%" if rdw else ""],
                "message": f"Hemoglobin is below standard reference threshold ({hb} g/dL). Very common in vegetarian Indian populations due to nutritional iron or B12 insufficiency.",
                "recommendation": "Screen serum ferritin, vitamin B12, and iron saturation with your doctor. Emphasize iron-rich vegetarian sources (spinach, lentils, dates) paired with Vitamin C."
            })
        else:
            flags.append({
                "category": "hematologic",
                "title": "Optimal Red Blood Cell & Hemoglobin",
                "status": "optimal",
                "markers": [f"Hemoglobin: {hb} g/dL"],
                "message": "Oxygen-carrying capacity and red blood cell indices are healthy.",
                "recommendation": "Maintain adequate dietary iron and leafy greens."
            })

    # 6. Systemic Inflammation (hs-CRP)
    crp = biomarkers.get("crp")
    if crp is not None:
        if crp >= 3.0:
            flags.append({
                "category": "inflammation",
                "title": "Elevated Systemic Inflammation (hs-CRP)",
                "status": "elevated",
                "markers": [f"hs-CRP: {crp} mg/L"],
                "message": "High-sensitivity C-Reactive Protein is elevated. Indicates active low-grade vascular or systemic inflammation.",
                "recommendation": "Discuss with your physician to evaluate potential inflammatory or infection causes, improve sleep hygiene, and adopt an anti-inflammatory diet."
            })
        elif crp >= 1.0:
            flags.append({
                "category": "inflammation",
                "title": "Moderate Systemic Inflammation",
                "status": "borderline",
                "markers": [f"hs-CRP: {crp} mg/L"],
                "message": "hs-CRP is in the average/moderate range.",
                "recommendation": "Regular aerobic exercise and stress management to keep vascular inflammation low."
            })
        else:
            flags.append({
                "category": "inflammation",
                "title": "Low Systemic Inflammation (Cardioprotective)",
                "status": "optimal",
                "markers": [f"hs-CRP: {crp} mg/L"],
                "message": "hs-CRP is below 1.0 mg/L, reflecting low baseline vascular inflammation.",
                "recommendation": "Maintain current lifestyle and anti-inflammatory nutrition."
            })

    return flags
