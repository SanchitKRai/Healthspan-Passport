"use client";

import React, { useState } from "react";
import { ExtractionResponse, AnalysisResponse } from "../types/biomarker";
import { UploadSection } from "../components/UploadSection";
import { PatientSummary } from "../components/PatientSummary";
import { ConfirmationTable } from "../components/ConfirmationTable";
import { PhenoAgeCard } from "../components/PhenoAgeCard";
import { RiskFlagsSection } from "../components/RiskFlagsSection";
import WhatIfSimulator from "../components/WhatIfSimulator";
import TrendsView from "../components/TrendsView";
import BilingualExplainer, { ExplanationData } from "../components/BilingualExplainer";
import ClinicianHandoff from "../components/ClinicianHandoff";
import { API_BASE_URL } from "../config/api";

export default function Home() {
  const [extractedData, setExtractedData] = useState<ExtractionResponse | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);
  const [explanation, setExplanation] = useState<ExplanationData | null>(null);
  const [isExplaining, setIsExplaining] = useState<boolean>(false);

  const handleReset = () => {
    setExtractedData(null);
    setAnalysisData(null);
    setExplanation(null);
  };

  const fetchExplanation = async (analysis: AnalysisResponse) => {
    setIsExplaining(true);
    try {
      const res = await fetch(`${API_BASE_URL}/api/explain`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chronological_age: analysis.chronological_age,
          patient_gender: analysis.patient_gender,
          phenoage: analysis.phenoage.phenoage,
          age_acceleration: analysis.phenoage.age_acceleration,
          risk_flags: analysis.risk_flags,
          biomarkers: analysis.normalized_biomarkers,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setExplanation(data);
      }
    } catch (err) {
      console.error("Failed to generate bilingual explanation:", err);
    } finally {
      setIsExplaining(false);
    }
  };

  const handleAnalysisSuccess = (analysis: AnalysisResponse) => {
    setAnalysisData(analysis);
    // Auto-generate bilingual explanation & doctor questions upon confirmation
    fetchExplanation(analysis);
  };

  // Convert normalized biomarkers to conventional clinical units for simulator sliders
  const getSimulatorInitialValues = (analysis: AnalysisResponse) => {
    const map: Record<string, number> = {};
    for (const b of analysis.normalized_biomarkers) {
      if (b.value !== null && b.value !== undefined) {
        map[b.standard_id] = b.value;
      }
    }

    // Normalized canonical units:
    // Glucose: mmol/L -> mg/dL (* 18.0182)
    // CRP: mg/dL -> mg/L (* 10.0)
    // Albumin: g/L -> g/dL (/ 10.0)
    // Creatinine: µmol/L -> mg/dL (/ 88.4)
    return {
      glucose_mg_dl: map["glucose_fasting"]
        ? Math.round(map["glucose_fasting"] * 18.0182)
        : map["glucose"]
        ? Math.round(map["glucose"] * 18.0182)
        : 110,
      crp_mg_l: map["crp"] ? Number((map["crp"] * 10.0).toFixed(1)) : 2.5,
      albumin_g_dl: map["albumin"] ? Number((map["albumin"] / 10.0).toFixed(1)) : 4.0,
      lymphocyte_pct: map["lymphocyte_pct"] ?? 28.0,
      wbc_k_ul: map["wbc"] ?? 7.8,
      rdw_pct: map["rdw"] ?? 13.5,
      creatinine_mg_dl: map["creatinine"] ? Number((map["creatinine"] / 88.4).toFixed(2)) : 0.95,
      mcv_fl: map["mcv"] ?? 89.0,
      alp_u_l: map["alp"] ?? 75.0,
    };
  };

  return (
    <div className="space-y-8">
      {!extractedData && (
        <>
          <UploadSection
            onExtractionSuccess={(result) => {
              setExtractedData(result);
              setAnalysisData(null);
              setExplanation(null);
            }}
          />

          {/* Longitudinal Trends Explorer (Available even before upload for immediate demonstration) */}
          <div className="pt-4 border-t border-slate-200">
            <TrendsView />
          </div>
        </>
      )}

      {extractedData && (
        <section>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-bold text-slate-900">Report Analysis & Human Confirmation</h2>
              <p className="text-xs text-slate-500">
                Step 1: Review & confirm values. Step 2: Explore biological age, preventive risks, What-If simulator, and bilingual guidance.
              </p>
            </div>
            <button
              onClick={handleReset}
              className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-1.5 rounded font-medium transition-colors"
            >
              ← Upload Another Report
            </button>
          </div>

          <PatientSummary
            patient={extractedData.patient_info}
            metadata={extractedData.extraction_metadata}
          />

          {/* Analysis Dashboard (renders after user confirmation) */}
          {analysisData && (
            <div className="my-8 space-y-6">
              {/* Biological Age vs Chronological Age Card */}
              <PhenoAgeCard
                phenoageResult={analysisData.phenoage}
                chronologicalAge={analysisData.chronological_age}
                populationCaveat={analysisData.population_caveat}
              />

              {/* Multi-Organ Risk Flags */}
              <RiskFlagsSection riskFlags={analysisData.risk_flags} />

              {/* Task 1/2: Clinician One-Page PDF & FHIR R4 Action Bar */}
              <ClinicianHandoff
                analysis={analysisData}
                patientInfo={extractedData.patient_info}
                explanation={explanation}
              />

              {/* Module 4: Plain-Language Bilingual Explainer & Voice Narration */}
              <BilingualExplainer
                explanation={explanation}
                isLoading={isExplaining}
                onGenerate={() => fetchExplanation(analysisData)}
              />

              {/* Module 3A: Interactive What-If Longevity Simulator */}
              <WhatIfSimulator
                chronologicalAge={analysisData.chronological_age}
                initialValues={getSimulatorInitialValues(analysisData)}
              />

              {/* Module 3B: Longitudinal Healthspan & Biomarker Trends */}
              <TrendsView
                currentAnalysis={{
                  chronologicalAge: analysisData.chronological_age,
                  phenoage: analysisData.phenoage.phenoage,
                  ageAcceleration: analysisData.phenoage.age_acceleration,
                  biomarkers: getSimulatorInitialValues(analysisData),
                }}
              />
            </div>
          )}

          {/* Human-in-the-Loop Confirmation & Value Editing */}
          <ConfirmationTable
            initialBiomarkers={extractedData.biomarkers}
            patient={extractedData.patient_info}
            onAnalysisSuccess={handleAnalysisSuccess}
          />
        </section>
      )}
    </div>
  );
}
