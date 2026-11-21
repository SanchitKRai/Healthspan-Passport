import React from "react";
import { PatientInfo, ExtractionMetadata } from "../types/biomarker";

interface PatientSummaryProps {
  patient: PatientInfo;
  metadata: ExtractionMetadata;
}

export const PatientSummary: React.FC<PatientSummaryProps> = ({ patient, metadata }) => {
  return (
    <div className="border p-4 mb-6 rounded bg-gray-50 text-sm">
      <h2 className="font-semibold text-base mb-2">Extraction Summary & Patient Info</h2>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div>
          <span className="text-gray-500 block">Patient Name:</span>
          <span className="font-medium">{patient.name || "Not specified"}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Age / Gender:</span>
          <span className="font-medium">
            {patient.age ? `${patient.age} yrs` : "N/A"} / {patient.gender || "N/A"}
          </span>
        </div>
        <div>
          <span className="text-gray-500 block">Report Date:</span>
          <span className="font-medium">{patient.report_date || "N/A"}</span>
        </div>
        <div>
          <span className="text-gray-500 block">Laboratory:</span>
          <span className="font-medium">{patient.lab_name || "N/A"}</span>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t text-xs text-gray-600 flex flex-wrap gap-4">
        <span><strong>Model:</strong> {metadata.model_used}</span>
        <span><strong>Duration:</strong> {metadata.extraction_duration_ms} ms</span>
        <span><strong>Total Extracted:</strong> {metadata.total_biomarkers_found} markers</span>
        <span><strong>Review Flags:</strong> {metadata.low_confidence_count}</span>
      </div>

      {metadata.missing_phenoage_biomarkers.length > 0 && (
        <div className="mt-2 text-xs text-amber-700 bg-amber-50 p-2 rounded border border-amber-200">
          <strong>Missing PhenoAge Markers in Report:</strong>{" "}
          {metadata.missing_phenoage_biomarkers.join(", ")}
        </div>
      )}
    </div>
  );
};
