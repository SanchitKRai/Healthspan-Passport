import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.schemas.biomarker import (
    ExtractionResponse,
    AnalysisRequest,
    AnalysisResponse,
    PhenoAgeResult,
    RiskFlagItem,
    BiomarkerItem,
    ExplanationRequest,
    ExplanationResponse,
    ClinicalExportRequest,
)
from app.extraction.extractor import extract_text_from_file
from app.llm.client import extract_biomarkers_with_llm
from app.llm.chat import ChatRequest, ChatResponse, answer_health_question
from app.core.normalizer import normalize_biomarker
from app.core.phenoage import calculate_phenoage, evaluate_risk_flags
from app.core.explainer import generate_bilingual_explanation
from app.core.exporter import generate_clinician_pdf, generate_fhir_bundle

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("healthspan-api")

app = FastAPI(
    title="Healthspan Passport API",
    description="Laboratory biomarker extraction and preventive health analytics API",
    version="1.0.0",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Directory for sample reports (relative to repo root)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_REPORTS_DIR = REPO_ROOT / "data" / "sample_reports"


@app.get("/api/health")
def health_check() -> Dict[str, str]:
    return {"status": "healthy", "service": "Healthspan Passport Extraction API"}


@app.post("/api/extract", response_model=ExtractionResponse)
def extract_report(file: UploadFile = File(...)) -> ExtractionResponse:
    """Upload a PDF or image blood test report and extract structured biomarker data."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload")

    contents = file.file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    logger.info(f"Extracting text from uploaded file: {file.filename} ({len(contents)} bytes)")
    raw_text, extract_meta = extract_text_from_file(contents, file.filename)

    if extract_meta.get("error") and not raw_text.strip():
        raise HTTPException(
            status_code=422,
            detail=f"Failed to parse file {file.filename}: {extract_meta.get('error')}"
        )

    logger.info(f"Text extracted ({len(raw_text)} chars). Calling biomarker extraction LLM pipeline...")
    extraction_result = extract_biomarkers_with_llm(raw_text)
    return extraction_result


@app.get("/api/sample-reports")
def list_sample_reports() -> List[Dict[str, Any]]:
    """List pre-loaded sample reports available for demo testing."""
    samples = []
    if SAMPLE_REPORTS_DIR.exists():
        for f in sorted(SAMPLE_REPORTS_DIR.iterdir()):
            if f.is_file() and f.suffix.lower() in [".pdf", ".png", ".jpg", ".jpeg"]:
                format_type = "pdf" if f.suffix.lower() == ".pdf" else "image"
                clean_name = f.stem.replace("_", " ").title()
                samples.append({
                    "id": f.stem,
                    "filename": f.name,
                    "label": clean_name,
                    "format": format_type,
                    "size_bytes": f.stat().st_size
                })
    return samples


@app.post("/api/extract-sample/{filename}", response_model=ExtractionResponse)
def extract_sample_report(filename: str) -> ExtractionResponse:
    """Extract biomarkers directly from one of the pre-loaded sample reports."""
    file_path = SAMPLE_REPORTS_DIR / filename
    if not file_path.resolve().is_relative_to(SAMPLE_REPORTS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample report {filename} not found")

    file_bytes = file_path.read_bytes()
    raw_text, _ = extract_text_from_file(file_bytes, filename)
    return extract_biomarkers_with_llm(raw_text)


POPULATION_CAVEAT_NOTE = (
    "Clinical & Population Limitation Note: The PhenoAge biological age algorithm was developed "
    "and validated on the US population (NHANES III and IV cohorts). Reference ranges have been "
    "adapted for Indian clinical standards, but biological age calculations for Indian users should "
    "be interpreted as informational estimates and not definitive clinical or diagnostic measurements. "
    "Always discuss comprehensive health assessments with a qualified medical professional."
)


@app.post("/api/analyze", response_model=AnalysisResponse)
def analyze_biomarkers(req: AnalysisRequest) -> AnalysisResponse:
    """
    Accepts confirmed biomarker values and chronological age, performs unit normalization,
    computes Levine (2018) PhenoAge, and assesses multi-organ preventive risk flags.
    """
    normalized_list = []
    pheno_inputs: Dict[str, Any] = {}
    risk_inputs: Dict[str, Any] = {}

    for b in req.biomarkers:
        if b.value is not None:
            norm_val, norm_unit, ref_range = normalize_biomarker(
                b.standard_id.value,
                b.value,
                b.unit,
                sex=req.patient_gender
            )
            norm_item = BiomarkerItem(
                standard_id=b.standard_id,
                display_name=b.display_name,
                raw_name=b.raw_name,
                value=norm_val,
                unit=norm_unit,
                standard_unit=norm_unit,
                reference_range=ref_range,
                confidence=b.confidence,
                flag=b.flag,
                needs_review=b.needs_review,
                source_text=b.source_text,
                bounding_box=b.bounding_box,
            )
            normalized_list.append(norm_item)
            pheno_inputs[b.standard_id.value] = norm_val
            risk_inputs[b.standard_id.value] = b.value
            if b.standard_id.value == "glucose_fasting":
                risk_inputs["glucose"] = b.value

    pheno_res_dict = calculate_phenoage(pheno_inputs, req.chronological_age)
    pheno_result = PhenoAgeResult(**pheno_res_dict)
    flags_list = evaluate_risk_flags(risk_inputs, sex=req.patient_gender)
    risk_flags = [RiskFlagItem(**f) for f in flags_list]

    return AnalysisResponse(
        chronological_age=req.chronological_age,
        patient_gender=req.patient_gender,
        phenoage=pheno_result,
        risk_flags=risk_flags,
        normalized_biomarkers=normalized_list,
        population_caveat=POPULATION_CAVEAT_NOTE,
    )


@app.post("/api/explain", response_model=ExplanationResponse)
def explain_biomarkers(req: ExplanationRequest) -> ExplanationResponse:
    """Generate bilingual plain-language explanations and doctor questions."""
    return generate_bilingual_explanation(req)


@app.post("/api/chat", response_model=ChatResponse)
def chat_with_healthspan_companion(req: ChatRequest) -> ChatResponse:
    """Answer an educational question using only the confirmed report context supplied."""
    try:
        return answer_health_question(req)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@app.post("/api/export/pdf")
def export_clinician_pdf(req: ClinicalExportRequest):
    """Generate a single-page clinician handoff PDF."""
    pdf_bytes = generate_clinician_pdf(req)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=Healthspan_Passport_Clinical_Summary.pdf"}
    )


@app.post("/api/export/fhir")
def export_fhir_bundle(req: ClinicalExportRequest) -> Dict[str, Any]:
    """Generate an HL7 FHIR R4 Bundle with LOINC observation codes."""
    return generate_fhir_bundle(req)
