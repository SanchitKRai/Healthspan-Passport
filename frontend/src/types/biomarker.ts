/**
 * Healthspan Passport - Biomarker JSON Schema Specification (Contract v1.0 & Analysis Extensions)
 */

export enum CanonicalBiomarker {
  ALBUMIN = "albumin",
  CREATININE = "creatinine",
  GLUCOSE_FASTING = "glucose_fasting",
  CRP = "crp",
  LYMPHOCYTE_PCT = "lymphocyte_pct",
  MCV = "mcv",
  RDW = "rdw",
  ALP = "alp",
  WBC = "wbc",
  HEMOGLOBIN = "hemoglobin",
  PLATELETS = "platelets",
  HBA1C = "hba1c",
  CHOLESTEROL_TOTAL = "cholesterol_total",
  CHOLESTEROL_HDL = "cholesterol_hdl",
  CHOLESTEROL_LDL = "cholesterol_ldl",
  TRIGLYCERIDES = "triglycerides",
  VLDL = "vldl",
  BILIRUBIN_TOTAL = "bilirubin_total",
  AST_SGOT = "ast_sgot",
  ALT_SGPT = "alt_sgpt",
  BUN = "bun",
  URIC_ACID = "uric_acid",
  EGFR = "egfr",
  SODIUM = "sodium",
  POTASSIUM = "potassium",
  OTHER = "other",
}

export type BiomarkerFlag = "low" | "normal" | "high" | "critical" | "unknown";

export interface ReferenceRange {
  low: number | null;
  high: number | null;
  text: string | null;
}

export interface BoundingBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface BiomarkerItem {
  standard_id: CanonicalBiomarker;
  display_name: string;
  raw_name: string;
  value: number | null;
  unit: string;
  standard_unit: string;
  reference_range?: ReferenceRange | null;
  confidence: number;
  flag: BiomarkerFlag;
  needs_review: boolean;
  source_text?: string | null;
  bounding_box?: BoundingBox | null;
}

export interface PatientInfo {
  name: string | null;
  age: number | null;
  gender: string | null;
  report_date: string | null;
  lab_name: string | null;
}

export interface ExtractionMetadata {
  model_used: string;
  extraction_duration_ms: number;
  raw_text_length: number;
  total_biomarkers_found: number;
  low_confidence_count: number;
  missing_phenoage_biomarkers: string[];
}

export interface ExtractionResponse {
  patient_info: PatientInfo;
  biomarkers: BiomarkerItem[];
  extraction_metadata: ExtractionMetadata;
}

export interface SampleReportItem {
  id: string;
  filename: string;
  label: string;
  format: "pdf" | "image";
  size_bytes?: number;
}

export interface PhenoAgeResult {
  is_valid: boolean;
  phenoage: number | null;
  age_acceleration: number | null;
  mortality_score_10yr: number | null;
  missing_markers: string[];
  message: string;
}

export interface RiskFlagItem {
  category: string;
  title: string;
  status: "optimal" | "borderline" | "elevated";
  markers: string[];
  message: string;
  recommendation: string;
}

export interface AnalysisRequest {
  chronological_age: number;
  patient_gender?: string | null;
  biomarkers: BiomarkerItem[];
}

export interface AnalysisResponse {
  chronological_age: number;
  patient_gender?: string | null;
  phenoage: PhenoAgeResult;
  risk_flags: RiskFlagItem[];
  normalized_biomarkers: BiomarkerItem[];
  population_caveat: string;
}
