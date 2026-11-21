"use client";

import React, { useState } from "react";
import { API_BASE_URL } from "../config/api";
import { AnalysisResponse, ExtractionResponse } from "../types/biomarker";
import { ExplanationData } from "./BilingualExplainer";

interface ClinicianHandoffProps {
  analysis: AnalysisResponse;
  patientInfo?: ExtractionResponse["patient_info"];
  explanation?: ExplanationData | null;
}

export default function ClinicianHandoff({
  analysis,
  patientInfo,
  explanation,
}: ClinicianHandoffProps) {
  const [downloadingPdf, setDownloadingPdf] = useState(false);
  const [exportingFhir, setExportingFhir] = useState(false);
  const [fhirData, setFhirData] = useState<any | null>(null);
  const [showFhirModal, setShowFhirModal] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const buildExportPayload = () => {
    return {
      patient_info: patientInfo || {
        age: analysis.chronological_age,
        gender: analysis.patient_gender,
      },
      chronological_age: analysis.chronological_age,
      patient_gender: analysis.patient_gender,
      phenoage: analysis.phenoage,
      biomarkers: analysis.normalized_biomarkers,
      risk_flags: analysis.risk_flags,
      questions_for_doctor: explanation?.questions_for_doctor_en || [
        "Based on these biomarker results, do you recommend measuring HbA1c to evaluate insulin resistance?",
        "Given the current hs-CRP level, what further cardiovascular or inflammatory evaluation do you advise?",
        "What specific lifestyle modifications and testing timeline (e.g., 90 days) do you suggest before medication?",
      ],
      population_caveat: analysis.population_caveat,
    };
  };

  const handleDownloadPdf = async () => {
    setDownloadingPdf(true);
    setError(null);
    try {
      const payload = buildExportPayload();
      const res = await fetch(`${API_BASE_URL}/api/export/pdf`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to generate Clinician PDF handoff.");
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const patientName = patientInfo?.name ? patientInfo.name.replace(/\s+/g, "_") : "Patient";
      a.download = `Healthspan_Passport_Clinical_Summary_${patientName}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed downloading PDF.");
    } finally {
      setDownloadingPdf(false);
    }
  };

  const handleExportFhir = async () => {
    setExportingFhir(true);
    setError(null);
    try {
      const payload = buildExportPayload();
      const res = await fetch(`${API_BASE_URL}/api/export/fhir`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Failed to generate FHIR R4 Bundle.");
      }

      const data = await res.json();
      setFhirData(data);
      setShowFhirModal(true);

      // Also trigger file download
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `Healthspan_Passport_FHIR_R4_Bundle.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err: any) {
      console.error(err);
      setError(err.message || "Failed exporting FHIR JSON.");
    } finally {
      setExportingFhir(false);
    }
  };

  const handleCopyFhir = () => {
    if (!fhirData) return;
    navigator.clipboard.writeText(JSON.stringify(fhirData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm my-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xl">🩺</span>
            <h3 className="text-lg font-bold text-slate-900">
              Telemedicine & Clinician Handoff Export
            </h3>
            <span className="bg-emerald-50 text-emerald-700 text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border border-emerald-200">
              FHIR R4 / LOINC Ready
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-xl">
            Export a high-density, single-page PDF clinical summary tailored for telemedicine doctors, or generate an HL7 FHIR R4 JSON bundle for hospital electronic health records (EHR).
          </p>
        </div>

        <div className="flex flex-wrap gap-2 w-full md:w-auto">
          {/* 1-Page PDF Button */}
          <button
            onClick={handleDownloadPdf}
            disabled={downloadingPdf}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold px-4 py-2.5 rounded shadow-sm transition-colors disabled:opacity-50"
          >
            {downloadingPdf ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Rendering 1-Page PDF...</span>
              </>
            ) : (
              <>
                <span>📄</span>
                <span>Download 1-Page Doctor PDF</span>
              </>
            )}
          </button>

          {/* FHIR R4 JSON Export Button */}
          <button
            onClick={handleExportFhir}
            disabled={exportingFhir}
            className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-900 text-white text-xs font-semibold px-4 py-2.5 rounded shadow-sm transition-colors disabled:opacity-50"
          >
            {exportingFhir ? (
              <>
                <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
                <span>Packaging FHIR R4...</span>
              </>
            ) : (
              <>
                <span>⚡</span>
                <span>Export FHIR R4 JSON</span>
              </>
            )}
          </button>

          {fhirData && (
            <button
              onClick={() => setShowFhirModal(true)}
              className="text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 px-3 py-2.5 rounded font-medium border border-slate-200 transition-colors"
            >
              View FHIR Inspector
            </button>
          )}
        </div>
      </div>

      {error && (
        <div className="mt-4 p-3 bg-rose-50 border border-rose-200 text-xs text-rose-700 rounded">
          {error}
        </div>
      )}

      {/* FHIR JSON Inspector Modal */}
      {showFhirModal && fhirData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-xs">
          <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[85vh] flex flex-col border border-slate-200">
            {/* Modal Header */}
            <div className="flex justify-between items-center px-5 py-3.5 border-b border-slate-200 bg-slate-50 rounded-t-lg">
              <div className="flex items-center gap-2">
                <span className="font-bold text-slate-900 text-sm">
                  HL7 FHIR R4 Observation Bundle
                </span>
                <span className="text-[11px] bg-blue-100 text-blue-800 font-mono px-2 py-0.5 rounded">
                  {fhirData.entry?.length || 0} entries
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleCopyFhir}
                  className="text-xs bg-white border border-slate-300 hover:bg-slate-100 px-2.5 py-1 rounded font-medium text-slate-700 transition-colors"
                >
                  {copied ? "✓ Copied!" : "Copy JSON"}
                </button>
                <button
                  onClick={() => setShowFhirModal(false)}
                  className="text-slate-400 hover:text-slate-700 font-bold text-lg leading-none p-1"
                >
                  ✕
                </button>
              </div>
            </div>

            {/* Modal Body: Formatted Code */}
            <div className="p-4 overflow-y-auto font-mono text-xs bg-slate-950 text-slate-200 flex-1">
              <pre>{JSON.stringify(fhirData, null, 2)}</pre>
            </div>

            {/* Modal Footer */}
            <div className="px-5 py-3 border-t border-slate-200 bg-slate-50 flex justify-between items-center text-xs text-slate-600 rounded-b-lg">
              <span>Standardized LOINC and UCUM units mapped for EHR interoperability.</span>
              <button
                onClick={() => setShowFhirModal(false)}
                className="bg-slate-800 hover:bg-slate-900 text-white font-medium px-4 py-1.5 rounded transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
