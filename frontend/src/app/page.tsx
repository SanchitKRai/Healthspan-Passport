"use client";

import React, { useState } from "react";
import { ExtractionResponse, AnalysisResponse } from "../types/biomarker";
import { UploadSection } from "../components/UploadSection";
import { PatientSummary } from "../components/PatientSummary";
import { ConfirmationTable } from "../components/ConfirmationTable";
import { PhenoAgeCard } from "../components/PhenoAgeCard";
import { RiskFlagsSection } from "../components/RiskFlagsSection";

export default function Home() {
  const [extractedData, setExtractedData] = useState<ExtractionResponse | null>(null);
  const [analysisData, setAnalysisData] = useState<AnalysisResponse | null>(null);

  const handleReset = () => {
    setExtractedData(null);
    setAnalysisData(null);
  };

  return (
    <div>
      {!extractedData && (
        <UploadSection
          onExtractionSuccess={(result) => {
            setExtractedData(result);
            setAnalysisData(null);
          }}
        />
      )}

      {extractedData && (
        <section>
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-bold">Report Analysis & Human Confirmation</h2>
              <p className="text-xs text-gray-500">Step 1: Review & confirm values. Step 2: View biological age & preventive risks.</p>
            </div>
            <button
              onClick={handleReset}
              className="text-xs bg-gray-200 px-3 py-1.5 rounded hover:bg-gray-300 font-medium"
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
            <div className="mb-8">
              <PhenoAgeCard
                phenoageResult={analysisData.phenoage}
                chronologicalAge={analysisData.chronological_age}
                populationCaveat={analysisData.population_caveat}
              />

              <RiskFlagsSection riskFlags={analysisData.risk_flags} />
            </div>
          )}

          {/* Human-in-the-Loop Confirmation & Value Editing */}
          <ConfirmationTable
            initialBiomarkers={extractedData.biomarkers}
            patient={extractedData.patient_info}
            onAnalysisSuccess={(analysis) => setAnalysisData(analysis)}
          />
        </section>
      )}
    </div>
  );
}
