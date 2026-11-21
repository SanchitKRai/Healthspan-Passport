from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class CanonicalBiomarker(str, Enum):
    # Core PhenoAge Biomarkers (9 Blood Markers + Chronological Age)
    ALBUMIN = "albumin"
    CREATININE = "creatinine"
    GLUCOSE_FASTING = "glucose_fasting"
    CRP = "crp"
    LYMPHOCYTE_PCT = "lymphocyte_pct"
    MCV = "mcv"
    RDW = "rdw"
    ALP = "alp"
    WBC = "wbc"

    # Additional Routine Preventive & Metabolic Biomarkers
    HEMOGLOBIN = "hemoglobin"
    PLATELETS = "platelets"
    HBA1C = "hba1c"
    CHOLESTEROL_TOTAL = "cholesterol_total"
    CHOLESTEROL_HDL = "cholesterol_hdl"
    CHOLESTEROL_LDL = "cholesterol_ldl"
    TRIGLYCERIDES = "triglycerides"
    VLDL = "vldl"
    BILIRUBIN_TOTAL = "bilirubin_total"
    AST_SGOT = "ast_sgot"
    ALT_SGPT = "alt_sgpt"
    BUN = "bun"
    URIC_ACID = "uric_acid"
    EGFR = "egfr"
    SODIUM = "sodium"
    POTASSIUM = "potassium"
    OTHER = "other"


PHENOAGE_CORE_BIOMARKERS = {
    CanonicalBiomarker.ALBUMIN.value,
    CanonicalBiomarker.CREATININE.value,
    CanonicalBiomarker.GLUCOSE_FASTING.value,
    CanonicalBiomarker.CRP.value,
    CanonicalBiomarker.LYMPHOCYTE_PCT.value,
    CanonicalBiomarker.MCV.value,
    CanonicalBiomarker.RDW.value,
    CanonicalBiomarker.ALP.value,
    CanonicalBiomarker.WBC.value,
}


class BiomarkerFlag(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class ReferenceRange(BaseModel):
    low: Optional[float] = None
    high: Optional[float] = None
    text: Optional[str] = None


class BoundingBox(BaseModel):
    page: int = 1
    x0: float = 0.0
    y0: float = 0.0
    x1: float = 0.0
    y1: float = 0.0


# Biologically plausible physiological limits (below or above triggers critical review)
PHYSIOLOGICAL_LIMITS = {
    CanonicalBiomarker.ALBUMIN: (1.0, 7.5),
    CanonicalBiomarker.CREATININE: (0.2, 20.0),
    CanonicalBiomarker.GLUCOSE_FASTING: (30.0, 600.0),
    CanonicalBiomarker.CRP: (0.0, 300.0),
    CanonicalBiomarker.LYMPHOCYTE_PCT: (1.0, 95.0),
    CanonicalBiomarker.MCV: (40.0, 150.0),
    CanonicalBiomarker.RDW: (8.0, 35.0),
    CanonicalBiomarker.ALP: (10.0, 1500.0),
    CanonicalBiomarker.WBC: (0.5, 100.0),
    CanonicalBiomarker.HEMOGLOBIN: (3.0, 25.0),
    CanonicalBiomarker.PLATELETS: (10.0, 1500.0),
    CanonicalBiomarker.HBA1C: (3.0, 20.0),
    CanonicalBiomarker.CHOLESTEROL_TOTAL: (50.0, 800.0),
    CanonicalBiomarker.CHOLESTEROL_HDL: (10.0, 150.0),
    CanonicalBiomarker.CHOLESTEROL_LDL: (10.0, 600.0),
    CanonicalBiomarker.TRIGLYCERIDES: (20.0, 2000.0),
    CanonicalBiomarker.BILIRUBIN_TOTAL: (0.1, 40.0),
    CanonicalBiomarker.AST_SGOT: (2.0, 2000.0),
    CanonicalBiomarker.ALT_SGPT: (2.0, 2000.0),
    CanonicalBiomarker.BUN: (2.0, 200.0),
    CanonicalBiomarker.URIC_ACID: (1.0, 25.0),
}


class BiomarkerItem(BaseModel):
    standard_id: CanonicalBiomarker
    display_name: str
    raw_name: str
    value: Optional[float] = None
    unit: str
    standard_unit: str
    reference_range: Optional[ReferenceRange] = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    flag: BiomarkerFlag = BiomarkerFlag.NORMAL
    needs_review: bool = False
    source_text: Optional[str] = None
    bounding_box: Optional[BoundingBox] = None

    @model_validator(mode="after")
    def evaluate_needs_review(self) -> "BiomarkerItem":
        # Rule 1: Confidence < 0.8
        if self.confidence < 0.8:
            self.needs_review = True

        # Rule 2: Missing / unparsed value
        if self.value is None:
            self.needs_review = True
            return self

        # Rule 3: Physiological limit validation (Contract Rule 3)
        if self.standard_id in PHYSIOLOGICAL_LIMITS:
            min_val, max_val = PHYSIOLOGICAL_LIMITS[self.standard_id]
            if self.value < min_val or self.value > max_val:
                self.needs_review = True
                self.flag = BiomarkerFlag.CRITICAL

        return self


class PatientInfo(BaseModel):
    name: Optional[str] = None
    age: Optional[float] = None
    gender: Optional[str] = None
    report_date: Optional[str] = None
    lab_name: Optional[str] = None


class ExtractionMetadata(BaseModel):
    model_used: str
    extraction_duration_ms: int = 0
    raw_text_length: int = 0
    total_biomarkers_found: int = 0
    low_confidence_count: int = 0
    missing_phenoage_biomarkers: List[str] = Field(default_factory=list)


class ExtractionResponse(BaseModel):
    patient_info: PatientInfo
    biomarkers: List[BiomarkerItem]
    extraction_metadata: ExtractionMetadata


class PhenoAgeResult(BaseModel):
    is_valid: bool
    phenoage: Optional[float] = None
    age_acceleration: Optional[float] = None
    mortality_score_10yr: Optional[float] = None
    missing_markers: List[str] = Field(default_factory=list)
    message: str


class RiskFlagItem(BaseModel):
    category: str
    title: str
    status: str  # "optimal", "borderline", "elevated"
    markers: List[str] = Field(default_factory=list)
    message: str
    recommendation: str


class AnalysisRequest(BaseModel):
    chronological_age: float = Field(..., gt=0, lt=130)
    patient_gender: Optional[str] = None
    biomarkers: List[BiomarkerItem]


class AnalysisResponse(BaseModel):
    chronological_age: float
    patient_gender: Optional[str] = None
    phenoage: PhenoAgeResult
    risk_flags: List[RiskFlagItem]
    normalized_biomarkers: List[BiomarkerItem]
    population_caveat: str


class ExplanationRequest(BaseModel):
    chronological_age: float
    patient_gender: Optional[str] = None
    phenoage: Optional[float] = None
    age_acceleration: Optional[float] = None
    risk_flags: List[RiskFlagItem] = Field(default_factory=list)
    biomarkers: List[BiomarkerItem] = Field(default_factory=list)


class ExplanationResponse(BaseModel):
    summary_en: str
    summary_hi: str
    key_findings_en: List[str]
    key_findings_hi: List[str]
    dietary_guidance_en: List[str]
    dietary_guidance_hi: List[str]
    questions_for_doctor_en: List[str]
    questions_for_doctor_hi: List[str]
    disclaimer_en: str
    disclaimer_hi: str

