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
        # Any value with confidence < 0.8 requires manual confirmation
        if self.confidence < 0.8:
            self.needs_review = True
        if self.value is None:
            self.needs_review = True
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
