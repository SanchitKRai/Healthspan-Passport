"use client";

import React, { useState } from "react";
import { ExtractionResponse } from "../types/biomarker";
import { UploadSection } from "../components/UploadSection";
import { PatientSummary } from "../components/PatientSummary";
import { BiomarkerTable } from "../components/BiomarkerTable";

export default function Home() {
  const [data, setData] = useState<ExtractionResponse | null>(null);

  return (
    <div>
      <UploadSection onExtractionSuccess={(result) => setData(result)} />

      {data && (
        <section className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-bold">Extracted Biomarker Results</h2>
            <button
              onClick={() => setData(null)}
              className="text-xs bg-gray-200 px-3 py-1.5 rounded hover:bg-gray-300"
            >
              Reset / New Upload
            </button>
          </div>

          <PatientSummary
            patient={data.patient_info}
            metadata={data.extraction_metadata}
          />

          <BiomarkerTable biomarkers={data.biomarkers} />
        </section>
      )}
    </div>
  );
}
