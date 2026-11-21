"use client";

import React, { useState, useEffect } from "react";
import { API_BASE_URL } from "../config/api";
import { SampleReportItem, ExtractionResponse } from "../types/biomarker";

interface UploadSectionProps {
  onExtractionSuccess: (data: ExtractionResponse) => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ onExtractionSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [sampleReports, setSampleReports] = useState<SampleReportItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingTarget, setLoadingTarget] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  // Load sample reports from backend
  useEffect(() => {
    fetch(`${API_BASE_URL}/api/sample-reports`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not fetch samples");
        return res.json();
      })
      .then((data) => setSampleReports(data))
      .catch((err) => console.log("Sample reports listing:", err));
  }, []);

  const handleFileUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }

    setLoading(true);
    setLoadingTarget("file");
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Extraction failed");
      }

      const result: ExtractionResponse = await response.json();
      onExtractionSuccess(result);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during extraction");
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const extractSampleNamed = async (filename: string) => {
    setLoading(true);
    setLoadingTarget(filename);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/extract-sample/${filename}`, {
        method: "POST",
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Sample extraction failed");
      }

      const result: ExtractionResponse = await response.json();
      onExtractionSuccess(result);
    } catch (err: any) {
      setError(err.message || "Failed extracting sample report");
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const handleSampleSelect = () => {
    if (!selectedSample) {
      setError("Please choose a sample report from the dropdown.");
      return;
    }
    extractSampleNamed(selectedSample);
  };

  return (
    <div className="border border-slate-200 p-6 rounded-lg mb-8 bg-white shadow-sm">
      {/* 1-Click Quick Demo Banner */}
      <div className="mb-6 p-4 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-blue-600 font-bold">⚡ Hackathon Judge Quick Demo:</span>
            <span className="text-xs bg-blue-100 text-blue-800 font-semibold px-2 py-0.5 rounded">1-Click Test</span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Test the entire pipeline instantly with a real Indian lab panel (Metropolis Healthcare: Impaired fasting glucose, elevated hs-CRP, and dyslipidemia).
          </p>
        </div>
        <button
          type="button"
          onClick={() => extractSampleNamed("02_metropolis_prediabetic.pdf")}
          disabled={loading}
          className="whitespace-nowrap bg-blue-600 hover:bg-blue-700 text-white font-semibold text-xs px-4 py-2.5 rounded shadow-sm transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          {loading && loadingTarget === "02_metropolis_prediabetic.pdf" ? (
            <>
              <svg className="animate-spin h-3.5 w-3.5 text-white" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <span>Analyzing Demo Report...</span>
            </>
          ) : (
            <>
              <span>🚀</span>
              <span>Launch Live Pre-Diabetic Demo</span>
            </>
          )}
        </button>
      </div>

      <h2 className="text-lg font-bold text-slate-900 mb-4">Or Upload Any Blood Report</h2>

      {error && (
        <div className="p-3 mb-4 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-500 font-bold ml-2">✕</button>
        </div>
      )}

      {loading && (
        <div className="mb-6 p-4 rounded-lg bg-slate-50 border border-slate-200 text-center animate-pulse">
          <div className="inline-block p-2 bg-blue-100 text-blue-700 rounded-full mb-2">
            <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
            </svg>
          </div>
          <div className="text-sm font-semibold text-slate-800">
            Extracting Biomarkers & Running Dual-Model LLM Parser...
          </div>
          <div className="text-xs text-slate-500 mt-1">
            Running OCR text extraction, regex bounding, and physiological range verification.
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User File Upload */}
        <div className="border-b md:border-b-0 md:border-r border-slate-200 pb-6 md:pb-0 md:pr-6">
          <h3 className="font-semibold text-sm text-slate-800 mb-1">Option A: Upload Your PDF or Photo</h3>
          <p className="text-xs text-slate-500 mb-3">Accepts digital laboratory PDFs and phone photos (JPEG/PNG).</p>
          <form onSubmit={handleFileUpload} className="space-y-3">
            <input
              type="file"
              accept=".pdf,image/png,image/jpeg,image/jpg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-xs border border-slate-300 p-2 rounded cursor-pointer file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-slate-100 file:text-slate-700"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !file}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading && loadingTarget === "file" ? "Extracting from File..." : "Extract from File"}
            </button>
          </form>
        </div>

        {/* Pre-loaded Sample Selector */}
        <div>
          <h3 className="font-semibold text-sm text-slate-800 mb-1">Option B: Choose from 15 Test Samples</h3>
          <p className="text-xs text-slate-500 mb-3">Includes Dr. Lal, Metropolis, Apollo, Quest, plus skewed phone captures.</p>
          <div className="space-y-3">
            <select
              value={selectedSample}
              onChange={(e) => setSelectedSample(e.target.value)}
              className="block w-full text-xs border border-slate-300 p-2 rounded bg-white text-slate-800"
              disabled={loading}
            >
              <option value="">-- Select a test report ({sampleReports.length} available) --</option>
              {sampleReports.map((sample) => (
                <option key={sample.filename} value={sample.filename}>
                  {sample.label} ({sample.format.toUpperCase()})
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={handleSampleSelect}
              disabled={loading || !selectedSample}
              className="w-full bg-slate-800 text-white py-2 px-4 rounded text-xs font-semibold hover:bg-slate-900 disabled:opacity-50 transition-colors"
            >
              {loading && loadingTarget === selectedSample ? "Extracting Sample..." : "Load Selected Sample Report"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
