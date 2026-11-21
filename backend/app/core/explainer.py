"""
Plain-Language Bilingual Explainer Engine (English & Hindi)
Generates structured, strictly non-diagnostic summaries, key findings,
Indian vegetarian dietary optimizations, and targeted doctor discussion questions.
"""

from typing import List, Dict, Any, Optional
from app.schemas.biomarker import (
    ExplanationRequest,
    ExplanationResponse,
    RiskFlagItem,
    BiomarkerItem,
)


def generate_bilingual_explanation(req: ExplanationRequest) -> ExplanationResponse:
    """
    Produces evidence-grounded bilingual summaries in English and Hindi.
    Adheres to strict non-diagnostic clinical communication guidelines.
    """
    age = req.chronological_age
    phenoage = req.phenoage
    accel = req.age_acceleration
    risk_flags = req.risk_flags or []
    biomarkers = req.biomarkers or []

    # Map biomarkers by standard_id for fast lookup
    bio_map: Dict[str, BiomarkerItem] = {b.standard_id: b for b in biomarkers if b.standard_id}

    # 1. Summary Synthesis (English & Hindi)
    if phenoage is not None and accel is not None:
        if accel <= -1.0:
            summary_en = (
                f"Your estimated biological age is {phenoage:.1f} years, which is {abs(accel):.1f} years younger "
                f"than your chronological age ({age:.0f} years). Your multi-system laboratory biomarkers demonstrate "
                f"favorable cellular resilience and lower-than-average 10-year biological vulnerability."
            )
            summary_hi = (
                f"आपकी अनुमानित जैविक आयु (PhenoAge) {phenoage:.1f} वर्ष है, जो आपकी वास्तविक कालानुक्रमिक आयु ({age:.0f} वर्ष) "
                f"से {abs(accel):.1f} वर्ष कम है। आपके रक्त परीक्षण मार्कर बेहतर कोशिकीय स्वास्थ्य और उत्कृष्ट जैविक गतिशीलता दर्शाते हैं।"
            )
        elif accel >= 1.0:
            summary_en = (
                f"Your estimated biological age is {phenoage:.1f} years, which is {accel:.1f} years higher "
                f"than your chronological age ({age:.0f} years). Key cardiometabolic, inflammatory, or hematologic "
                f"markers indicate physiological strain that can be actively improved through targeted lifestyle and dietary interventions."
            )
            summary_hi = (
                f"आपकी अनुमानित जैविक आयु (PhenoAge) {phenoage:.1f} वर्ष है, जो आपकी वास्तविक कालानुक्रमिक आयु ({age:.0f} वर्ष) "
                f"से {accel:.1f} वर्ष अधिक है। कुछ चयापचय (मेटाबॉलिक) या सूजन संबंधी मार्कर शारीरिक तनाव का संकेत दे रहे हैं, "
                f"जिन्हें जीवनशैली और आहार में उचित बदलाव करके सुधारा जा सकता है।"
            )
        else:
            summary_en = (
                f"Your estimated biological age is {phenoage:.1f} years, closely aligning with your chronological "
                f"age ({age:.0f} years, delta of {accel:+.1f} years). Your biomarker profile reflects steady baseline aging."
            )
            summary_hi = (
                f"आपकी अनुमानित जैविक आयु (PhenoAge) {phenoage:.1f} वर्ष है, जो आपकी वास्तविक आयु ({age:.0f} वर्ष) "
                f"के लगभग बराबर है (अंतर {accel:+.1f} वर्ष)। आपकी शारीरिक उम्र बढ़ने की गति सामान्य संतुलन में है।"
            )
    else:
        summary_en = (
            f"Based on your submitted clinical report for age {age:.0f}, individual organ-system risk indicators "
            f"were evaluated. A complete 9-marker panel (including hs-CRP and differential CBC) is needed to compute overall biological age."
        )
        summary_hi = (
            f"आपकी आयु ({age:.0f} वर्ष) के आधार पर आपके उपलब्ध रक्त परीक्षणों का विश्लेषण किया गया है। "
            f"संपूर्ण जैविक आयु (PhenoAge) की गणना के लिए hs-CRP सहित पूरे 9 मार्करों की आवश्यकता होती है।"
        )

    # 2. Key Findings (English & Hindi)
    key_findings_en: List[str] = []
    key_findings_hi: List[str] = []

    # Check metabolic/glycemic markers
    glucose_item = bio_map.get("glucose_fasting") or bio_map.get("glucose")
    hba1c_item = bio_map.get("hba1c")
    if (glucose_item and glucose_item.value and glucose_item.value >= 100.0) or (hba1c_item and hba1c_item.value and hba1c_item.value >= 5.7):
        val_str = f"Fasting glucose {glucose_item.value} mg/dL" if glucose_item and glucose_item.value else ""
        if hba1c_item and hba1c_item.value:
            val_str += f"{', ' if val_str else ''}HbA1c {hba1c_item.value}%"
        key_findings_en.append(
            f"Glycemic Regulation: {val_str}. Values are above optimal fasting thresholds, indicating early insulin resistance or pre-diabetes tendency."
        )
        key_findings_hi.append(
            f"रक्त शर्करा (ग्लूकोज): {val_str}। यह स्तर सामान्य सीमा से थोड़ा ऊपर है, जो शुरुआती इंसुलिन प्रतिरोध या प्री-डायबिटीज की ओर संकेत करता है।"
        )
    elif glucose_item and glucose_item.value:
        key_findings_en.append(
            f"Glycemic Regulation: Fasting glucose is optimal ({glucose_item.value} mg/dL)."
        )
        key_findings_hi.append(
            f"रक्त शर्करा (ग्लूकोज): फास्टिंग ग्लूकोज का स्तर स्वस्थ और सामान्य ({glucose_item.value} mg/dL) है।"
        )

    # Check inflammation (hs-CRP)
    crp_item = bio_map.get("crp")
    if crp_item and crp_item.value:
        if crp_item.value > 3.0:
            key_findings_en.append(
                f"Systemic Inflammation: hs-CRP is elevated at {crp_item.value} mg/L (> 3.0 mg/L), signaling low-grade systemic inflammation and increased cardiovascular strain."
            )
            key_findings_hi.append(
                f"सूजन मार्कर (hs-CRP): स्तर {crp_item.value} mg/L है, जो शरीर में सूजन और हृदय संबंधी तनाव में वृद्धि का संकेत देता है।"
            )
        elif crp_item.value <= 1.0:
            key_findings_en.append(
                f"Systemic Inflammation: hs-CRP is in the optimal low-risk tier ({crp_item.value} mg/L), indicating low systemic vascular inflammation."
            )
            key_findings_hi.append(
                f"सूजन मार्कर (hs-CRP): स्तर {crp_item.value} mg/L है, जो न्यूनतम सूजन और उत्कृष्ट वाहिका स्वास्थ्य दर्शाता है।"
            )

    # Check lipid profile (cholesterol, triglycerides)
    chol_item = bio_map.get("total_cholesterol")
    tg_item = bio_map.get("triglycerides")
    if (chol_item and chol_item.value and chol_item.value > 200) or (tg_item and tg_item.value and tg_item.value > 150):
        key_findings_en.append(
            "Lipid Balance: Elevated total cholesterol or triglycerides. Worth discussing an ApoB or lipid particle evaluation with your doctor."
        )
        key_findings_hi.append(
            "लिपिड प्रोफाइल (कोलेस्ट्रॉल): कोलेस्ट्रॉल या ट्राइग्लिसराइड्स का स्तर बढ़ा हुआ है। डॉक्टर से लिपिड प्रबंधन पर चर्चा करें।"
        )

    # Check renal markers (creatinine, egfr)
    creat_item = bio_map.get("creatinine")
    if creat_item and creat_item.value and creat_item.value > 1.2:
        key_findings_en.append(
            f"Renal Function: Serum creatinine is slightly elevated ({creat_item.value} mg/dL). Ensure adequate hydration and check renal clearance."
        )
        key_findings_hi.append(
            f"गुर्दे (किडनी) का स्वास्थ्य: सीरम क्रिएटिनिन ({creat_item.value} mg/dL) थोड़ा बढ़ा हुआ है। पर्याप्त पानी पिएं और डॉक्टर से सलाह लें।"
        )

    # Fallback findings if sparse data
    if not key_findings_en:
        key_findings_en.append("Comprehensive Organ Panels: Most reviewed biomarkers fall within expected physiological ranges.")
        key_findings_hi.append("समग्र अंग स्वास्थ्य: अधिकांश परीक्षण मार्कर सामान्य शारीरिक सीमा के भीतर हैं।")

    # 3. Evidence-Based Indian Dietary Guidance (Vegetarian-Friendly)
    dietary_guidance_en: List[str] = [
        "Carbohydrate Optimization: Substitute refined polished white rice and maida with low-glycemic traditional Indian grains (foxtail millet, ragi, bajra) and whole sprouted moong or chana to flatten glucose spikes.",
        "Anti-Inflammatory Culinary Spices: Combine fresh turmeric (curcumin) with cracked black pepper (piperine) in daily warm preparations, and increase omega-3 intake via crushed flaxseeds (alsi) and walnuts.",
        "Vegetarian Iron Bioavailability: When having iron-rich vegetarian meals (spinach, methi, moringa, beetroot), immediately pair with natural Vitamin C (amla, freshly squeezed lemon juice) to enhance non-heme iron absorption.",
        "Lean Protein Distribution: Aim for 20-25g of bioavailable protein per meal via low-fat paneer, Greek curd, sattu, tofu, or roasted chana to maintain metabolic muscle mass as you age.",
    ]

    dietary_guidance_hi: List[str] = [
        "अनाज का सही चुनाव: सफेद पॉलिश चावल और मैदे की जगह पारंपरिक मोटे अनाज (ज्वार, बाजरा, रागी, फॉक्सटेल मिलेट) और साबुत अंकुरित मूंग/चना खाएं ताकि ब्लड शुगर में उतार-चढ़ाव न हो।",
        "एंटी-इन्फ्लेमेटरी मसाले: दैनिक आहार में हल्दी को थोड़ी काली मिर्च के साथ लें, जिससे हल्दी का असर कई गुना बढ़ता है। अलसी और अखरोट से ओमेगा-3 प्राप्त करें।",
        "आयरन का बेहतर अवशोषण: हरी पत्तेदार सब्जियों (पालक, मेथी, सहजन) के साथ नींबू का रस या आंवला अवश्य लें; विटामिन सी पौधों से मिलने वाले आयरन को शरीर में आसानी से सोखने में मदद करता है।",
        "शाकाहारी प्रोटीन: मांसपेशियों को मजबूत रखने के लिए हर भोजन में पनीर, दही, सत्तू, अंकुरित दालें या भुना चना जैसे प्रोटीन स्रोतों को शामिल करें।",
    ]

    # 4. 3-5 Specific Questions to Ask Your Doctor
    questions_for_doctor_en: List[str] = [
        "Based on these biomarker results and my biological age trajectory, do you recommend performing an HbA1c test or an oral glucose challenge to evaluate insulin resistance?",
        "Given my current hs-CRP and lipid readings, what is my 10-year atherosclerotic cardiovascular disease (ASCVD) risk score, and would an ApoB or CAC scan be helpful?",
        "Would focused dietary and exercise modifications be the appropriate first step, and what specific clinical targets should we aim for over the next 90 days?",
        "Do you recommend checking micronutrient baselines—specifically Serum Vitamin B12, 25-OH Vitamin D, and Ferritin—which frequently impact metabolic and immune health in Indian diets?",
        "When would you recommend a follow-up blood panel (e.g., 3 months vs. 6 months) to monitor progress?",
    ]

    questions_for_doctor_hi: List[str] = [
        "मेरी इन रिपोर्टों और जैविक आयु के आधार पर, क्या मुझे इंसुलिन प्रतिरोध की जांच के लिए HbA1c परीक्षण करवाना चाहिए?",
        "मेरे hs-CRP और कोलेस्ट्रॉल स्तर को देखते हुए, क्या मुझे हृदय स्वास्थ्य से संबंधित किसी अतिरिक्त जांच की आवश्यकता है?",
        "दवाएं शुरू करने से पहले क्या 90 दिनों के लिए आहार सुधार और नियमित व्यायाम की रणनीति अपनाना उपयुक्त रहेगा?",
        "क्या मुझे विटामिन डी3, विटामिन बी12 और सीरम फेरिटिन की जांच करानी चाहिए, जो भारतीय आहार में अक्सर कम पाए जाते हैं?",
        "प्रगति और सुधार की निगरानी के लिए इन परीक्षणों को कितने समय बाद (3 या 6 महीने में) दोबारा दोहराना चाहिए?",
    ]

    disclaimer_en = (
        "This biological age and healthspan summary is generated solely for educational, preventive, and physician-handoff purposes. "
        "It does not provide medical diagnoses, treatment decisions, or prescriptions. Always consult a qualified physician or registered medical specialist."
    )

    disclaimer_hi = (
        "यह जैविक आयु और स्वास्थ्य रिपोर्ट केवल शैक्षणिक, रोकथाम और डॉक्टर से परामर्श की सुविधा के लिए तैयार की गई है। "
        "यह किसी भी रोग का चिकित्सकीय निदान या दवा का नुस्खा नहीं है। हमेशा योग्य चिकित्सक से व्यक्तिगत परामर्श अवश्य लें।"
    )

    return ExplanationResponse(
        summary_en=summary_en,
        summary_hi=summary_hi,
        key_findings_en=key_findings_en,
        key_findings_hi=key_findings_hi,
        dietary_guidance_en=dietary_guidance_en,
        dietary_guidance_hi=dietary_guidance_hi,
        questions_for_doctor_en=questions_for_doctor_en,
        questions_for_doctor_hi=questions_for_doctor_hi,
        disclaimer_en=disclaimer_en,
        disclaimer_hi=disclaimer_hi,
    )
