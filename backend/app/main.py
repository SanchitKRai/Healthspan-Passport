import os
import logging
from pathlib import Path
from typing import List, Dict, Any
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.schemas.biomarker import ExtractionResponse
from app.extraction.extractor import extract_text_from_file
from app.llm.client import extract_biomarkers_with_llm

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
async def extract_report(file: UploadFile = File(...)) -> ExtractionResponse:
    """Upload a PDF or image blood test report and extract structured biomarker data."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename missing from upload")

    contents = await file.read()
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
                # Generate clean human label
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
    # Prevent directory traversal
    if not file_path.resolve().is_relative_to(SAMPLE_REPORTS_DIR.resolve()):
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail=f"Sample report {filename} not found")

    file_bytes = file_path.read_bytes()
    raw_text, _ = extract_text_from_file(file_bytes, filename)
    return extract_biomarkers_with_llm(raw_text)
