import os
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "data" / "sample_reports"
GROUND_TRUTH_FILE = REPO_ROOT / "data" / "ground_truth.json"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Define 15 distinct report profiles with ground truth
REPORT_PROFILES = [
    {
        "filename": "01_dr_lal_healthy_adult.pdf",
        "format": "pdf",
        "lab": "Dr Lal PathLabs",
        "patient": {"name": "Aarav Sharma", "age": 34, "gender": "male", "date": "2026-11-10"},
        "biomarkers": [
            {"id": "albumin", "name": "Serum Albumin", "val": 4.5, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 0.9, "unit": "mg/dL", "ref": "0.7 - 1.2", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Fasting Blood Glucose", "val": 88.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
            {"id": "crp", "name": "hs-CRP", "val": 0.8, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "normal"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes %", "val": 32.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "Mean Corpuscular Volume (MCV)", "val": 89.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW-CV", "val": 12.8, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "Alkaline Phosphatase (ALP)", "val": 78.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "Total Leukocyte Count (WBC)", "val": 6.8, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "hemoglobin", "name": "Hemoglobin", "val": 15.2, "unit": "g/dL", "ref": "13.0 - 17.5", "flag": "normal"},
        ]
    },
    {
        "filename": "02_metropolis_prediabetic.pdf",
        "format": "pdf",
        "lab": "Metropolis Healthcare",
        "patient": {"name": "Vikram Malhotra", "age": 47, "gender": "male", "date": "2026-11-12"},
        "biomarkers": [
            {"id": "glucose_fasting", "name": "Fasting Glucose", "val": 118.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "high"},
            {"id": "hba1c", "name": "HbA1c Glycated Hemoglobin", "val": 6.2, "unit": "%", "ref": "4.0 - 5.6", "flag": "high"},
            {"id": "triglycerides", "name": "Triglycerides", "val": 195.0, "unit": "mg/dL", "ref": "0 - 150", "flag": "high"},
            {"id": "cholesterol_total", "name": "Total Cholesterol", "val": 215.0, "unit": "mg/dL", "ref": "125 - 200", "flag": "high"},
            {"id": "albumin", "name": "Serum Albumin", "val": 4.2, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 1.1, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "normal"},
            {"id": "crp", "name": "hs-CRP", "val": 2.8, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "high"},
            {"id": "wbc", "name": "Total WBC Count", "val": 8.4, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 91.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW", "val": 13.4, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "ALP", "val": 86.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes", "val": 28.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
        ]
    },
    {
        "filename": "03_apollo_anemia_female.pdf",
        "format": "pdf",
        "lab": "Apollo Diagnostics",
        "patient": {"name": "Pooja Verma", "age": 28, "gender": "female", "date": "2026-11-14"},
        "biomarkers": [
            {"id": "hemoglobin", "name": "Hemoglobin (Hb)", "val": 9.4, "unit": "g/dL", "ref": "12.0 - 15.5", "flag": "low"},
            {"id": "mcv", "name": "Mean Corpuscular Volume (MCV)", "val": 71.5, "unit": "fL", "ref": "80 - 100", "flag": "low"},
            {"id": "rdw", "name": "RDW-CV", "val": 16.8, "unit": "%", "ref": "11.5 - 14.5", "flag": "high"},
            {"id": "albumin", "name": "Albumin", "val": 3.9, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Creatinine", "val": 0.7, "unit": "mg/dL", "ref": "0.5 - 1.1", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Fasting Glucose", "val": 82.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
            {"id": "crp", "name": "C-Reactive Protein", "val": 1.1, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "high"},
            {"id": "lymphocyte_pct", "name": "Lymphocyte %", "val": 35.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 65.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "WBC", "val": 5.8, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
        ]
    },
    {
        "filename": "04_srl_renal_risk.pdf",
        "format": "pdf",
        "lab": "SRL Diagnostics",
        "patient": {"name": "Kailash Chand", "age": 62, "gender": "male", "date": "2026-11-15"},
        "biomarkers": [
            {"id": "creatinine", "name": "Serum Creatinine", "val": 1.9, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "high"},
            {"id": "bun", "name": "Blood Urea Nitrogen (BUN)", "val": 34.0, "unit": "mg/dL", "ref": "7 - 20", "flag": "high"},
            {"id": "uric_acid", "name": "Serum Uric Acid", "val": 8.6, "unit": "mg/dL", "ref": "3.5 - 7.2", "flag": "high"},
            {"id": "albumin", "name": "Albumin", "val": 3.7, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Glucose Fasting", "val": 96.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
            {"id": "crp", "name": "hs-CRP", "val": 3.4, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "high"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes", "val": 22.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 88.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW", "val": 14.1, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "ALP", "val": 92.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "WBC", "val": 7.4, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
        ]
    },
    {
        "filename": "05_max_liver_inflammation.pdf",
        "format": "pdf",
        "lab": "Max Healthcare Laboratory",
        "patient": {"name": "Rajesh Singhania", "age": 44, "gender": "male", "date": "2026-11-16"},
        "biomarkers": [
            {"id": "alt_sgpt", "name": "ALT / SGPT", "val": 82.0, "unit": "U/L", "ref": "7 - 56", "flag": "high"},
            {"id": "ast_sgot", "name": "AST / SGOT", "val": 68.0, "unit": "U/L", "ref": "10 - 40", "flag": "high"},
            {"id": "bilirubin_total", "name": "Total Bilirubin", "val": 1.6, "unit": "mg/dL", "ref": "0.2 - 1.2", "flag": "high"},
            {"id": "crp", "name": "hs-CRP", "val": 5.2, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "high"},
            {"id": "albumin", "name": "Serum Albumin", "val": 4.0, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Creatinine", "val": 1.0, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Fasting Sugar", "val": 104.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "high"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes", "val": 24.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 94.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW", "val": 13.9, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 135.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "Total Leukocytes", "val": 9.2, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
        ]
    },
    {
        "filename": "06_quest_missing_crp.pdf",
        "format": "pdf",
        "lab": "Quest Diagnostics",
        "patient": {"name": "Deepa Nair", "age": 51, "gender": "female", "date": "2026-11-17"},
        "biomarkers": [
            {"id": "albumin", "name": "Albumin, Serum", "val": 4.3, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Creatinine, Serum", "val": 0.8, "unit": "mg/dL", "ref": "0.5 - 1.1", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Glucose, Fasting", "val": 91.0, "unit": "mg/dL", "ref": "65 - 99", "flag": "normal"},
            # CRP IS DELIBERATELY OMITTED TO TEST MISSING PHENOAGE INPUT WARNING
            {"id": "lymphocyte_pct", "name": "Lymphocytes %", "val": 30.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 87.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW", "val": 12.6, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 72.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "White Blood Cell Count", "val": 6.1, "unit": "10^3/uL", "ref": "3.8 - 10.8", "flag": "normal"},
            {"id": "cholesterol_total", "name": "Total Cholesterol", "val": 182.0, "unit": "mg/dL", "ref": "125 - 200", "flag": "normal"},
            {"id": "cholesterol_hdl", "name": "HDL Cholesterol", "val": 56.0, "unit": "mg/dL", "ref": "> 50", "flag": "normal"},
        ]
    },
    {
        "filename": "07_suburban_geriatric.pdf",
        "format": "pdf",
        "lab": "Suburban Diagnostics",
        "patient": {"name": "Harishchandra Rao", "age": 73, "gender": "male", "date": "2026-11-18"},
        "biomarkers": [
            {"id": "albumin", "name": "Serum Albumin", "val": 3.6, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 1.35, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "high"},
            {"id": "glucose_fasting", "name": "Fasting Blood Sugar", "val": 112.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "high"},
            {"id": "crp", "name": "C-Reactive Protein (hs-CRP)", "val": 4.1, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "high"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes", "val": 19.0, "unit": "%", "ref": "20 - 40", "flag": "low"},
            {"id": "mcv", "name": "MCV", "val": 96.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW-CV", "val": 15.2, "unit": "%", "ref": "11.5 - 14.5", "flag": "high"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 105.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "Total WBC", "val": 7.9, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
        ]
    },
    {
        "filename": "08_medall_young_athlete.pdf",
        "format": "pdf",
        "lab": "Medall Healthcare",
        "patient": {"name": "Rohan Mehra", "age": 23, "gender": "male", "date": "2026-11-19"},
        "biomarkers": [
            {"id": "albumin", "name": "Serum Albumin", "val": 4.8, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 0.95, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Fasting Glucose", "val": 84.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
            {"id": "crp", "name": "hs-CRP", "val": 0.4, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "normal"},
            {"id": "lymphocyte_pct", "name": "Lymphocyte Count %", "val": 36.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 88.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW", "val": 12.0, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 68.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "wbc", "name": "Total Leukocytes", "val": 5.4, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "hemoglobin", "name": "Hemoglobin", "val": 16.1, "unit": "g/dL", "ref": "13.0 - 17.5", "flag": "normal"},
        ]
    },
    # 7 Mobile Phone Captured / Simulated Skewed Images
    {
        "filename": "09_phone_photo_cbc_skewed.jpg",
        "format": "image",
        "lab": "City Care Diagnostic Center",
        "skew_deg": -3.5,
        "patient": {"name": "Kavita Reddy", "age": 36, "gender": "female", "date": "2026-11-15"},
        "biomarkers": [
            {"id": "wbc", "name": "WBC Count", "val": 6.5, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "hemoglobin", "name": "Hemoglobin", "val": 13.1, "unit": "g/dL", "ref": "12.0 - 15.5", "flag": "normal"},
            {"id": "lymphocyte_pct", "name": "Lymphocytes %", "val": 31.0, "unit": "%", "ref": "20 - 40", "flag": "normal"},
            {"id": "mcv", "name": "MCV", "val": 89.0, "unit": "fL", "ref": "80 - 100", "flag": "normal"},
            {"id": "rdw", "name": "RDW-CV", "val": 13.0, "unit": "%", "ref": "11.5 - 14.5", "flag": "normal"},
            {"id": "platelets", "name": "Platelets", "val": 240.0, "unit": "10^3/uL", "ref": "150 - 450", "flag": "normal"},
        ]
    },
    {
        "filename": "10_phone_photo_metabolic_shadow.jpg",
        "format": "image",
        "lab": "Lifeline Pathology Lab",
        "shadow": True,
        "patient": {"name": "Arun Kumar", "age": 55, "gender": "male", "date": "2026-11-16"},
        "biomarkers": [
            {"id": "glucose_fasting", "name": "Fasting Blood Sugar", "val": 126.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "high"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 1.2, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "normal"},
            {"id": "bun", "name": "Urea", "val": 28.0, "unit": "mg/dL", "ref": "15 - 40", "flag": "normal"},
            {"id": "uric_acid", "name": "Uric Acid", "val": 6.8, "unit": "mg/dL", "ref": "3.5 - 7.2", "flag": "normal"},
        ]
    },
    {
        "filename": "11_phone_photo_lipid_creased.jpg",
        "format": "image",
        "lab": "HealthFirst Diagnostics",
        "creased": True,
        "patient": {"name": "Meera Joshi", "age": 49, "gender": "female", "date": "2026-11-17"},
        "biomarkers": [
            {"id": "cholesterol_total", "name": "Total Cholesterol", "val": 235.0, "unit": "mg/dL", "ref": "125 - 200", "flag": "high"},
            {"id": "cholesterol_hdl", "name": "HDL Cholesterol", "val": 42.0, "unit": "mg/dL", "ref": "40 - 60", "flag": "normal"},
            {"id": "cholesterol_ldl", "name": "LDL Cholesterol", "val": 154.0, "unit": "mg/dL", "ref": "0 - 100", "flag": "high"},
            {"id": "triglycerides", "name": "Triglycerides", "val": 195.0, "unit": "mg/dL", "ref": "0 - 150", "flag": "high"},
        ]
    },
    {
        "filename": "12_phone_photo_liver_angle.jpg",
        "format": "image",
        "lab": "Apex Health Diagnostics",
        "skew_deg": 2.8,
        "patient": {"name": "Gaurav Sen", "age": 41, "gender": "male", "date": "2026-11-18"},
        "biomarkers": [
            {"id": "bilirubin_total", "name": "Total Bilirubin", "val": 1.4, "unit": "mg/dL", "ref": "0.2 - 1.2", "flag": "high"},
            {"id": "ast_sgot", "name": "SGOT (AST)", "val": 54.0, "unit": "U/L", "ref": "10 - 40", "flag": "high"},
            {"id": "alt_sgpt", "name": "SGPT (ALT)", "val": 72.0, "unit": "U/L", "ref": "7 - 56", "flag": "high"},
            {"id": "alp", "name": "Alkaline Phosphatase", "val": 110.0, "unit": "U/L", "ref": "44 - 147", "flag": "normal"},
            {"id": "albumin", "name": "Albumin", "val": 4.1, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
        ]
    },
    {
        "filename": "13_phone_photo_diabetes_panel.jpg",
        "format": "image",
        "lab": "Dr Batra Pathology",
        "skew_deg": -1.5,
        "patient": {"name": "Sunita Agarwal", "age": 60, "gender": "female", "date": "2026-11-19"},
        "biomarkers": [
            {"id": "glucose_fasting", "name": "Fasting Glucose", "val": 142.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "high"},
            {"id": "hba1c", "name": "HbA1c", "val": 7.4, "unit": "%", "ref": "4.0 - 5.6", "flag": "high"},
            {"id": "creatinine", "name": "Creatinine", "val": 1.0, "unit": "mg/dL", "ref": "0.5 - 1.1", "flag": "normal"},
        ]
    },
    {
        "filename": "14_phone_photo_routine_health_check.jpg",
        "format": "image",
        "lab": "Apollo Clinic",
        "shadow": True,
        "patient": {"name": "Naveen Chawla", "age": 31, "gender": "male", "date": "2026-11-20"},
        "biomarkers": [
            {"id": "albumin", "name": "Serum Albumin", "val": 4.4, "unit": "g/dL", "ref": "3.5 - 5.0", "flag": "normal"},
            {"id": "creatinine", "name": "Serum Creatinine", "val": 0.85, "unit": "mg/dL", "ref": "0.7 - 1.3", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Fasting Blood Sugar", "val": 86.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
            {"id": "crp", "name": "hs-CRP", "val": 0.9, "unit": "mg/L", "ref": "0.0 - 1.0", "flag": "normal"},
            {"id": "wbc", "name": "TLC (WBC)", "val": 6.2, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "hemoglobin", "name": "Hemoglobin", "val": 14.8, "unit": "g/dL", "ref": "13.0 - 17.5", "flag": "normal"},
        ]
    },
    {
        "filename": "15_phone_photo_low_contrast.jpg",
        "format": "image",
        "lab": "Care Diagnostics",
        "low_contrast": True,
        "patient": {"name": "Priyanka Roy", "age": 27, "gender": "female", "date": "2026-11-21"},
        "biomarkers": [
            {"id": "hemoglobin", "name": "Hemoglobin", "val": 12.4, "unit": "g/dL", "ref": "12.0 - 15.5", "flag": "normal"},
            {"id": "platelets", "name": "Platelet Count", "val": 210.0, "unit": "10^3/uL", "ref": "150 - 450", "flag": "normal"},
            {"id": "wbc", "name": "WBC", "val": 7.1, "unit": "10^3/uL", "ref": "4.0 - 11.0", "flag": "normal"},
            {"id": "glucose_fasting", "name": "Glucose", "val": 90.0, "unit": "mg/dL", "ref": "70 - 99", "flag": "normal"},
        ]
    }
]


def generate_pdf_report(profile: dict, output_path: Path):
    """Generate a clean, structured clinical laboratory PDF report."""
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    # Header Banner
    c.setFillColor(colors.HexColor("#1e3a8a"))
    c.rect(0, height - 70, width, 70, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, height - 42, profile["lab"])
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 58, "NABL Accredited Clinical Reference Laboratory")

    # Patient Details Box
    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.setFillColor(colors.HexColor("#f8fafc"))
    c.rect(40, height - 145, width - 80, 65, fill=True, stroke=True)

    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 10)
    pat = profile["patient"]
    c.drawString(55, height - 100, f"Patient Name: {pat['name']}")
    c.drawString(55, height - 118, f"Age / Gender: {pat['age']} Yrs / {pat['gender'].title()}")
    c.drawString(340, height - 100, f"Collection Date: {pat['date']}")
    c.drawString(340, height - 118, f"Report ID: HP-{hash(profile['filename']) % 1000000:06d}")

    # Biomarkers Table Header
    y = height - 175
    c.setFillColor(colors.HexColor("#0284c7"))
    c.rect(40, y, width - 80, 22, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(50, y + 6, "TEST DESCRIPTION")
    c.drawString(260, y + 6, "RESULT")
    c.drawString(340, y + 6, "UNITS")
    c.drawString(430, y + 6, "REFERENCE INTERVAL")

    y -= 20
    c.setFont("Helvetica", 9)
    for idx, bio in enumerate(profile["biomarkers"]):
        if idx % 2 == 1:
            c.setFillColor(colors.HexColor("#f1f5f9"))
            c.rect(40, y - 4, width - 80, 18, fill=True, stroke=False)

        c.setFillColor(colors.black)
        c.drawString(50, y, bio["name"])
        
        # Highlight abnormal values
        if bio.get("flag") in ["high", "low"]:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(260, y, f"{bio['val']} *")
        else:
            c.setFont("Helvetica", 9)
            c.drawString(260, y, str(bio["val"]))

        c.setFont("Helvetica", 9)
        c.drawString(340, y, bio["unit"])
        c.drawString(430, y, bio["ref"])
        y -= 20

    # Footer note
    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(colors.HexColor("#64748b"))
    c.drawString(40, 40, "* Values marked with an asterisk are outside typical biological reference intervals.")
    c.drawString(40, 28, "This electronic report is generated for Healthspan Passport validation and evaluation.")

    c.save()


def generate_image_report(profile: dict, output_path: Path):
    """Generate a realistic lab report image, simulating mobile phone camera captures."""
    img_w, img_h = 750, 600
    img = Image.new("RGB", (img_w, img_h), color=(250, 250, 248))
    draw = ImageDraw.Draw(img)

    # Simulated receipt / lab header
    draw.rectangle([0, 0, img_w, 60], fill=(24, 43, 73))
    draw.text((30, 18), profile["lab"].upper(), fill=(255, 255, 255))

    # Patient info
    pat = profile["patient"]
    draw.text((30, 80), f"PATIENT: {pat['name']}", fill=(30, 30, 30))
    draw.text((30, 105), f"AGE/SEX: {pat['age']} Y / {pat['gender'][0].upper()}", fill=(30, 30, 30))
    draw.text((400, 80), f"DATE: {pat['date']}", fill=(30, 30, 30))
    draw.line([(30, 135), (img_w - 30, 135)], fill=(180, 180, 180), width=2)

    # Table Header
    draw.text((35, 145), "INVESTIGATION", fill=(80, 80, 80))
    draw.text((320, 145), "VALUE", fill=(80, 80, 80))
    draw.text((430, 145), "UNIT", fill=(80, 80, 80))
    draw.text((540, 145), "REF RANGE", fill=(80, 80, 80))
    draw.line([(30, 170), (img_w - 30, 170)], fill=(200, 200, 200), width=1)

    y = 185
    for bio in profile["biomarkers"]:
        draw.text((35, y), bio["name"], fill=(15, 15, 15))
        draw.text((320, y), str(bio["val"]), fill=(15, 15, 15))
        draw.text((430, y), bio["unit"], fill=(40, 40, 40))
        draw.text((540, y), bio["ref"], fill=(60, 60, 60))
        y += 35

    # Simulated Mobile Phone Artifacts:
    # 1. Shadow overlay
    if profile.get("shadow"):
        shadow = Image.new("L", (img_w, img_h), 0)
        s_draw = ImageDraw.Draw(shadow)
        for x in range(img_w):
            alpha = int(70 * math.sin((x / img_w) * math.pi))
            s_draw.line([(x, 0), (x, img_h)], fill=alpha)
        # Apply shadow by darkening
        img = Image.composite(Image.new("RGB", (img_w, img_h), (200, 200, 195)), img, shadow)

    # 2. Skew / Rotation
    skew = profile.get("skew_deg", 0.0)
    if skew != 0.0:
        img = img.rotate(skew, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(240, 240, 240))

    # 3. Low contrast / blur filter
    if profile.get("low_contrast"):
        img = img.filter(ImageFilter.GaussianBlur(radius=0.4))

    img.save(str(output_path), quality=88)


def main():
    ground_truth = {}
    print(f"Generating 15 sample lab reports into {OUTPUT_DIR}...")

    for profile in REPORT_PROFILES:
        filename = profile["filename"]
        out_file = OUTPUT_DIR / filename
        
        if profile["format"] == "pdf":
            generate_pdf_report(profile, out_file)
        else:
            generate_image_report(profile, out_file)
        
        # Save to ground truth mapping
        ground_truth[filename] = {
            "lab": profile["lab"],
            "format": profile["format"],
            "patient": profile["patient"],
            "biomarkers": {
                b["id"]: {
                    "raw_name": b["name"],
                    "value": b["val"],
                    "unit": b["unit"],
                    "flag": b.get("flag", "normal")
                }
                for b in profile["biomarkers"]
            }
        }
        print(f"  [+] Created {filename} ({profile['format']})")

    # Write ground_truth.json
    with open(GROUND_TRUTH_FILE, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Successfully saved ground truth dataset to {GROUND_TRUTH_FILE}")


if __name__ == "__main__":
    main()
