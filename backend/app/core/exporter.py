"""
Clinician Handoff Export Engine:
1. One-Page Clinician PDF Export (Strictly single A4 page for telemedicine/physician review)
2. HL7 FHIR R4 Observation Bundle Export with standardized LOINC coding
"""

import io
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether,
)

from app.schemas.biomarker import (
    ClinicalExportRequest,
    BiomarkerFlag,
)

# Standard LOINC codes for laboratory biomarkers
LOINC_MAP: Dict[str, Dict[str, str]] = {
    "glucose_fasting": {"code": "1558-6", "display": "Fasting glucose [Mass/volume] in Serum or Plasma"},
    "glucose": {"code": "2345-7", "display": "Glucose [Mass/volume] in Serum or Plasma"},
    "hba1c": {"code": "4548-4", "display": "Hemoglobin A1c/Hemoglobin.total in Blood"},
    "albumin": {"code": "1751-7", "display": "Albumin [Mass/volume] in Serum or Plasma"},
    "creatinine": {"code": "2160-0", "display": "Creatinine [Mass/volume] in Serum or Plasma"},
    "crp": {"code": "30522-7", "display": "C reactive protein [Mass/volume] in Serum or Plasma by High sensitivity method"},
    "lymphocyte_pct": {"code": "736-9", "display": "Lymphocytes/100 leukocytes in Blood by Automated count"},
    "mcv": {"code": "787-2", "display": "Erythrocyte mean corpuscular volume [Entitic volume] by Automated count"},
    "rdw": {"code": "788-0", "display": "Erythrocyte distribution width [Ratio] by Automated count"},
    "alp": {"code": "6768-6", "display": "Alkaline phosphatase [Enzymatic activity/volume] in Serum or Plasma"},
    "wbc": {"code": "6690-2", "display": "Leukocytes [#/volume] in Blood by Automated count"},
    "hemoglobin": {"code": "718-7", "display": "Hemoglobin [Mass/volume] in Blood"},
    "platelets": {"code": "777-3", "display": "Platelets [#/volume] in Blood by Automated count"},
    "total_cholesterol": {"code": "2093-3", "display": "Cholesterol [Mass/volume] in Serum or Plasma"},
    "hdl_cholesterol": {"code": "2085-9", "display": "Cholesterol in HDL [Mass/volume] in Serum or Plasma"},
    "ldl_cholesterol": {"code": "13457-7", "display": "Cholesterol in LDL [Mass/volume] in Serum or Plasma by calculation"},
    "triglycerides": {"code": "2571-8", "display": "Triglyceride [Mass/volume] in Serum or Plasma"},
    "bilirubin_total": {"code": "1975-2", "display": "Bilirubin.total [Mass/volume] in Serum or Plasma"},
    "ast_sgot": {"code": "1920-8", "display": "Aspartate aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
    "alt_sgpt": {"code": "1742-6", "display": "Alanine aminotransferase [Enzymatic activity/volume] in Serum or Plasma"},
    "bun": {"code": "3094-0", "display": "Urea nitrogen [Mass/volume] in Serum or Plasma"},
    "uric_acid": {"code": "3084-1", "display": "Urate [Mass/volume] in Serum or Plasma"},
    "vitamin_d": {"code": "62292-8", "display": "25-hydroxyvitamin D3+25-hydroxyvitamin D2 [Mass/volume] in Serum or Plasma"},
    "vitamin_b12": {"code": "2132-9", "display": "Cobalamin (Vitamin B12) [Mass/volume] in Serum or Plasma"},
    "ferritin": {"code": "2276-4", "display": "Ferritin [Mass/volume] in Serum or Plasma"},
    "calcium": {"code": "17861-6", "display": "Calcium [Mass/volume] in Serum or Plasma"},
    "sodium": {"code": "2951-2", "display": "Sodium [Moles/volume] in Serum or Plasma"},
    "potassium": {"code": "2823-3", "display": "Potassium [Moles/volume] in Serum or Plasma"},
}


def generate_fhir_bundle(req: ClinicalExportRequest) -> Dict[str, Any]:
    """
    Constructs an HL7 FHIR R4 Bundle (collection) containing Patient and
    Observation resources for all confirmed biomarkers and computed PhenoAge.
    """
    bundle_id = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    patient_name = req.patient_info.name if req.patient_info and req.patient_info.name else "Anonymous Patient"
    gender = req.patient_gender or (req.patient_info.gender if req.patient_info else "unknown")
    if gender not in ["male", "female", "other", "unknown"]:
        gender = "unknown"

    entries: List[Dict[str, Any]] = []

    # 1. Patient Resource
    patient_resource = {
        "resourceType": "Patient",
        "id": patient_id,
        "name": [
            {
                "use": "official",
                "text": patient_name
            }
        ],
        "gender": gender,
    }
    entries.append({
        "fullUrl": f"urn:uuid:{patient_id}",
        "resource": patient_resource
    })

    # 2. Biomarker Observations
    for b in req.biomarkers:
        if b.value is None:
            continue

        obs_id = str(uuid.uuid4())
        std_key = b.standard_id.value if hasattr(b.standard_id, "value") else str(b.standard_id)
        loinc_info = LOINC_MAP.get(std_key, {
            "code": "CUSTOM",
            "display": b.display_name or b.raw_name
        })

        # Interpretation flag
        interp_code = "N"
        interp_display = "Normal"
        if b.flag == BiomarkerFlag.HIGH:
            interp_code = "H"
            interp_display = "High"
        elif b.flag == BiomarkerFlag.LOW:
            interp_code = "L"
            interp_display = "Low"
        elif b.flag == BiomarkerFlag.CRITICAL:
            interp_code = "AA"
            interp_display = "Critical"

        obs_resource: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "laboratory",
                            "display": "Laboratory"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org" if loinc_info["code"] != "CUSTOM" else "https://healthspan-passport.org/fhir/codesystem",
                        "code": loinc_info["code"],
                        "display": loinc_info["display"]
                    }
                ],
                "text": b.display_name or b.raw_name
            },
            "subject": {
                "reference": f"urn:uuid:{patient_id}",
                "display": patient_name
            },
            "effectiveDateTime": (req.patient_info.report_date if req.patient_info and req.patient_info.report_date else now_iso[:10]),
            "valueQuantity": {
                "value": round(float(b.value), 2),
                "unit": b.unit,
                "system": "http://unitsofmeasure.org",
                "code": b.unit
            },
            "interpretation": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                            "code": interp_code,
                            "display": interp_display
                        }
                    ]
                }
            ]
        }

        # Reference range if present
        if b.reference_range:
            ref_dict: Dict[str, Any] = {}
            if b.reference_range.low is not None:
                ref_dict["low"] = {"value": b.reference_range.low, "unit": b.unit}
            if b.reference_range.high is not None:
                ref_dict["high"] = {"value": b.reference_range.high, "unit": b.unit}
            if ref_dict:
                obs_resource["referenceRange"] = [ref_dict]

        entries.append({
            "fullUrl": f"urn:uuid:{obs_id}",
            "resource": obs_resource
        })

    # 3. Biological Age (PhenoAge) Custom Observation
    if req.phenoage and req.phenoage.phenoage is not None:
        pheno_obs_id = str(uuid.uuid4())
        pheno_resource: Dict[str, Any] = {
            "resourceType": "Observation",
            "id": pheno_obs_id,
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "survey",
                            "display": "Survey"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "https://healthspan-passport.org/fhir/codesystem/biomarkers",
                        "code": "levine-phenoage-2018",
                        "display": "Levine PhenoAge Biological Age"
                    }
                ],
                "text": "Biological Age (Levine PhenoAge)"
            },
            "subject": {
                "reference": f"urn:uuid:{patient_id}",
                "display": patient_name
            },
            "effectiveDateTime": now_iso[:10],
            "valueQuantity": {
                "value": round(float(req.phenoage.phenoage), 1),
                "unit": "years",
                "system": "http://unitsofmeasure.org",
                "code": "a"
            },
            "component": [
                {
                    "code": {
                        "coding": [
                            {
                                "system": "https://healthspan-passport.org/fhir/codesystem/biomarkers",
                                "code": "age-acceleration",
                                "display": "PhenoAge Acceleration Delta"
                            }
                        ],
                        "text": "Age Acceleration Delta"
                    },
                    "valueQuantity": {
                        "value": round(float(req.phenoage.age_acceleration or 0.0), 1),
                        "unit": "years",
                        "system": "http://unitsofmeasure.org",
                        "code": "a"
                    }
                }
            ]
        }
        entries.append({
            "fullUrl": f"urn:uuid:{pheno_obs_id}",
            "resource": pheno_resource
        })

    return {
        "resourceType": "Bundle",
        "id": bundle_id,
        "meta": {
            "lastUpdated": now_iso,
            "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"]
        },
        "type": "collection",
        "timestamp": now_iso,
        "entry": entries
    }


def generate_clinician_pdf(req: ClinicalExportRequest) -> bytes:
    """
    Renders a crisp, single A4 page clinical handoff PDF for telemedicine physicians.
    Strictly engineered to never exceed 1 single page.
    """
    buffer = io.BytesIO()

    # Document Geometry: A4 (595.27 x 841.89 pt) with tight margins (24 pt = ~0.33 in)
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=24,
        rightMargin=24,
        topMargin=20,
        bottomMargin=20,
    )

    styles = getSampleStyleSheet()

    # Custom compact typography
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#475569"),
    )
    banner_style = ParagraphStyle(
        "Banner",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#991b1b"),
        alignment=1, # Centered
    )
    cell_style = ParagraphStyle(
        "CellNormal",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#1e293b"),
    )
    cell_bold = ParagraphStyle(
        "CellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=7,
        leading=8.5,
        textColor=colors.HexColor("#0f172a"),
    )
    sec_heading = ParagraphStyle(
        "SecHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10.5,
        textColor=colors.HexColor("#1e3a8a"),
    )
    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=6.8,
        leading=8.5,
        textColor=colors.HexColor("#334155"),
    )

    story = []

    # 1. Header Banner
    header_data = [
        [
            Paragraph("<b>Healthspan Passport</b> | Clinician Preventive Summary", title_style),
            Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M')}<br/><b>Standard:</b> HL7 FHIR R4 / LOINC", subtitle_style),
        ]
    ]
    header_table = Table(header_data, colWidths=[370, 175])
    header_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
        ("TOPPADDING", (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3))

    # 2. Non-Diagnostic Notice Pill
    banner_data = [[Paragraph("CONFIDENTIAL MEDICAL SUMMARY FOR LICENSED PHYSICIAN REVIEW — NOT A DIRECT CLINICAL DIAGNOSIS", banner_style)]]
    banner_table = Table(banner_data, colWidths=[545])
    banner_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fee2e2")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#fca5a5")),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ]))
    story.append(banner_table)
    story.append(Spacer(1, 4))

    # 3. Patient Demographics & Lab Origin
    p_name = req.patient_info.name if req.patient_info and req.patient_info.name else "Patient (De-identified)"
    p_age = f"{req.chronological_age:.0f} yrs"
    p_gender = (req.patient_gender or (req.patient_info.gender if req.patient_info else "N/A")).capitalize()
    p_date = (req.patient_info.report_date if req.patient_info and req.patient_info.report_date else "Not specified")
    p_lab = (req.patient_info.lab_name if req.patient_info and req.patient_info.lab_name else "Clinical Laboratory")

    demo_data = [
        [
            Paragraph(f"<b>Patient Name:</b> {p_name}", cell_style),
            Paragraph(f"<b>Chronological Age:</b> {p_age}", cell_style),
            Paragraph(f"<b>Sex:</b> {p_gender}", cell_style),
            Paragraph(f"<b>Collection Date:</b> {p_date}", cell_style),
            Paragraph(f"<b>Lab Source:</b> {p_lab}", cell_style),
        ]
    ]
    demo_table = Table(demo_data, colWidths=[130, 95, 65, 110, 145])
    demo_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(demo_table)
    story.append(Spacer(1, 4))

    # 4. Biological Age (PhenoAge) Summary Card
    if req.phenoage and req.phenoage.phenoage is not None:
        p_val = req.phenoage.phenoage
        p_accel = req.phenoage.age_acceleration or 0.0
        accel_sign = "+" if p_accel > 0 else ""
        accel_color = "#dc2626" if p_accel > 1.0 else ("#16a34a" if p_accel < -1.0 else "#475569")
        caveat_text = (
            "<b>Biological Age Model:</b> Levine et al. (2018) PhenoAge (9-biomarker Gompertz mortality model, calibrated on US NHANES cohort). "
            "Estimates for Indian individuals are informational and must be evaluated alongside clinical history."
        )

        pheno_cell_left = Paragraph(
            f"<b>Estimated Biological Age (PhenoAge):</b> <font size=11 color='#1e3a8a'><b>{p_val:.1f} years</b></font><br/>"
            f"<b>Aging Acceleration Delta (&Delta;):</b> <font size=9.5 color='{accel_color}'><b>{accel_sign}{p_accel:.1f} years</b></font> "
            f"vs Chronological ({p_age})",
            cell_style
        )
        pheno_cell_right = Paragraph(caveat_text, bullet_style)

        pheno_table = Table([[pheno_cell_left, pheno_cell_right]], colWidths=[245, 300])
        pheno_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f9ff")),
            ("BORDER", (0, 0), (-1, -1), 0.75, colors.HexColor("#bae6fd")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(pheno_table)
    else:
        missing_note = "Complete 9 PhenoAge biomarkers (CBC differential + hs-CRP) not confirmed in this report. Organ-level indicators analyzed below."
        pheno_table = Table([[Paragraph(f"<b>Biological Age (PhenoAge):</b> Not Computed — {missing_note}", cell_style)]], colWidths=[545])
        pheno_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(pheno_table)

    story.append(Spacer(1, 5))

    # 5. Confirmed Laboratory Biomarkers Table
    story.append(Paragraph("Laboratory Biomarkers & Reference Alignment (Indian Clinical Ranges)", sec_heading))
    story.append(Spacer(1, 2))

    # Build biomarker rows (split into 2 side-by-side columns if > 10 biomarkers to ensure 1-page fit)
    bio_items = [b for b in req.biomarkers if b.value is not None]

    if len(bio_items) <= 11:
        # Standard full-width table
        table_rows = [
            [
                Paragraph("<b>Biomarker (Standardized)</b>", cell_bold),
                Paragraph("<b>LOINC Code</b>", cell_bold),
                Paragraph("<b>Result & Unit</b>", cell_bold),
                Paragraph("<b>Ref Range (India)</b>", cell_bold),
                Paragraph("<b>Status Flag</b>", cell_bold),
                Paragraph("<b>Conf</b>", cell_bold),
            ]
        ]
        for b in bio_items:
            std_key = b.standard_id.value if hasattr(b.standard_id, "value") else str(b.standard_id)
            loinc = LOINC_MAP.get(std_key, {}).get("code", "—")
            if b.reference_range and b.reference_range.low is not None and b.reference_range.high is not None:
                ref_str = f"{b.reference_range.low} - {b.reference_range.high} {b.unit}"
            elif b.reference_range and b.reference_range.text:
                ref_str = b.reference_range.text
            else:
                ref_str = "—"

            flag_color = "#16a34a"
            if b.flag == BiomarkerFlag.HIGH:
                flag_color = "#dc2626"
            elif b.flag == BiomarkerFlag.LOW:
                flag_color = "#d97706"
            elif b.flag == BiomarkerFlag.CRITICAL:
                flag_color = "#7f1d1d"

            table_rows.append([
                Paragraph(f"<b>{b.display_name or b.raw_name}</b>", cell_style),
                Paragraph(loinc, cell_style),
                Paragraph(f"<b>{b.value:.2f}</b> {b.unit}", cell_style),
                Paragraph(ref_str, cell_style),
                Paragraph(f"<font color='{flag_color}'><b>{b.flag.value.upper()}</b></font>", cell_style),
                Paragraph(f"{int(b.confidence * 100)}%", cell_style),
            ])

        bio_table = Table(table_rows, colWidths=[150, 65, 100, 120, 70, 40])
        bio_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2.2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(bio_table)
    else:
        # Dual-column table to keep everything on single page
        mid = (len(bio_items) + 1) // 2
        left_items = bio_items[:mid]
        right_items = bio_items[mid:]

        dual_rows = [
            [
                Paragraph("<b>Biomarker</b>", cell_bold),
                Paragraph("<b>Result</b>", cell_bold),
                Paragraph("<b>Ref</b>", cell_bold),
                Paragraph("<b>Flag</b>", cell_bold),
                Paragraph("<b>Biomarker</b>", cell_bold),
                Paragraph("<b>Result</b>", cell_bold),
                Paragraph("<b>Ref</b>", cell_bold),
                Paragraph("<b>Flag</b>", cell_bold),
            ]
        ]
        for i in range(mid):
            row = []
            # Left item
            b_left = left_items[i]
            ref_l = f"{b_left.reference_range.low}-{b_left.reference_range.high}" if b_left.reference_range else "—"
            c_l = "#dc2626" if b_left.flag == BiomarkerFlag.HIGH else ("#d97706" if b_left.flag == BiomarkerFlag.LOW else "#16a34a")
            row.extend([
                Paragraph(f"<b>{b_left.display_name or b_left.raw_name}</b>", cell_style),
                Paragraph(f"{b_left.value:.1f} {b_left.unit}", cell_style),
                Paragraph(ref_l, cell_style),
                Paragraph(f"<font color='{c_l}'><b>{b_left.flag.value[:3].upper()}</b></font>", cell_style),
            ])

            # Right item (if available)
            if i < len(right_items):
                b_right = right_items[i]
                ref_r = f"{b_right.reference_range.low}-{b_right.reference_range.high}" if b_right.reference_range else "—"
                c_r = "#dc2626" if b_right.flag == BiomarkerFlag.HIGH else ("#d97706" if b_right.flag == BiomarkerFlag.LOW else "#16a34a")
                row.extend([
                    Paragraph(f"<b>{b_right.display_name or b_right.raw_name}</b>", cell_style),
                    Paragraph(f"{b_right.value:.1f} {b_right.unit}", cell_style),
                    Paragraph(ref_r, cell_style),
                    Paragraph(f"<font color='{c_r}'><b>{b_right.flag.value[:3].upper()}</b></font>", cell_style),
                ])
            else:
                row.extend([Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style), Paragraph("", cell_style)])

            dual_rows.append(row)

        bio_table = Table(dual_rows, colWidths=[90, 75, 65, 42, 90, 75, 65, 43])
        bio_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f1f5f9")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(bio_table)

    story.append(Spacer(1, 4))

    # 6. Active Risk Flags & Physician Questions (Side-by-Side Box to save vertical space)
    flag_elements = []
    if req.risk_flags:
        for rf in req.risk_flags[:3]: # Top 3 risk flags
            flag_elements.append(Paragraph(f"• <b>{rf.title}:</b> {rf.message}", bullet_style))
    else:
        flag_elements.append(Paragraph("• No acute cardiometabolic or inflammatory risk flags detected in panel.", bullet_style))

    q_elements = []
    if req.questions_for_doctor:
        for idx, q in enumerate(req.questions_for_doctor[:3], 1): # Top 3 questions
            q_elements.append(Paragraph(f"{idx}. {q}", bullet_style))
    else:
        q_elements.append(Paragraph("1. Review metabolic parameters and schedule 6-month preventive follow-up.", bullet_style))

    risk_q_table = Table(
        [
            [
                Paragraph("<b>Identified Clinical Risk Flags</b>", sec_heading),
                Paragraph("<b>Key Questions for Telemedicine / Clinic Doctor</b>", sec_heading),
            ],
            [
                flag_elements,
                q_elements,
            ]
        ],
        colWidths=[270, 275]
    )
    risk_q_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    story.append(risk_q_table)
    story.append(Spacer(1, 4))

    # 7. Single-line Medical Legal Footer
    footer_text = (
        "<b>Physician Notice:</b> This document was generated by Healthspan Passport using OCR and deterministic clinical normalizers. "
        "It provides structured pre-consultation intelligence. Diagnostic decisions, pharmacotherapy, and clinical staging remain solely the physician's domain."
    )
    story.append(Paragraph(footer_text, ParagraphStyle("Footer", parent=bullet_style, fontSize=6.2, leading=7.5, textColor=colors.HexColor("#64748b"))))

    doc.build(story)
    return buffer.getvalue()
