"use client";

import React, { useState, useEffect, useCallback } from "react";
import {
  API_BASE_URL,
  API_CONFIG_ERROR,
  BACKEND_UNREACHABLE_MESSAGE,
  isNetworkUnreachableError,
} from "../config/api";
import { SampleReportItem, ExtractionResponse } from "../types/biomarker";

interface UploadSectionProps {
  onExtractionSuccess: (data: ExtractionResponse, isSyntheticDemo?: boolean) => void;
  allowCloudLlm?: boolean;
}

interface OutboundPreview {
  kind: "file" | "sample";
  sampleFilename?: string;
  outbound_text: string;
  zero_lines: boolean;
  kept_lines: number;
  total_lines: number;
  redacted_categories: string[];
}

export const UploadSection: React.FC<UploadSectionProps> = ({
  onExtractionSuccess,
  allowCloudLlm = false,
}) => {
  const [file, setFile] = useState<File | null>(null);
  const [sampleReports, setSampleReports] = useState<SampleReportItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [loadingTarget, setLoadingTarget] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [backendUnreachable, setBackendUnreachable] = useState<boolean>(Boolean(API_CONFIG_ERROR));
  const [pendingPreview, setPendingPreview] = useState<OutboundPreview | null>(null);
  const [lastAction, setLastAction] = useState<(() => void) | null>(null);

  const loadSampleReports = useCallback(() => {
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setBackendUnreachable(true);
      return;
    }
    fetch(`${API_BASE_URL}/api/sample-reports`)
      .then((res) => {
        if (!res.ok) throw new Error("Could not fetch samples");
        return res.json();
      })
      .then((data) => {
        setSampleReports(data);
        setBackendUnreachable(false);
      })
      .catch(() => {
        setBackendUnreachable(true);
      });
  }, []);

  useEffect(() => {
    loadSampleReports();
  }, [loadSampleReports]);

  const executeFileExtraction = async (useCloud: boolean) => {
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setBackendUnreachable(true);
      setError(API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE);
      return;
    }

    setLoading(true);
    setLoadingTarget("file");
    setError(null);
    setLastAction(() => () => executeFileExtraction(useCloud));

    const formData = new FormData();
    formData.append("file", file);
    formData.append("allow_cloud_llm", String(useCloud));

    try {
      const response = await fetch(`${API_BASE_URL}/api/extract`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Extraction failed");
      }

      setBackendUnreachable(false);
      const result: ExtractionResponse = await response.json();
      onExtractionSuccess(result, false);
    } catch (err: unknown) {
      if (isNetworkUnreachableError(err)) {
        setBackendUnreachable(true);
        setError(BACKEND_UNREACHABLE_MESSAGE);
      } else {
        setError(err instanceof Error ? err.message : "An unexpected error occurred during extraction");
      }
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const executeSampleExtraction = async (filename: string, useCloud: boolean) => {
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setBackendUnreachable(true);
      setError(API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE);
      return;
    }

    setLoading(true);
    setLoadingTarget(filename);
    setError(null);
    setLastAction(() => () => executeSampleExtraction(filename, useCloud));

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/extract-sample/${encodeURIComponent(filename)}?allow_cloud_llm=${useCloud}`,
        { method: "POST" }
      );

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Sample extraction failed");
      }

      setBackendUnreachable(false);
      const result: ExtractionResponse = await response.json();
      onExtractionSuccess(result, true);
    } catch (err: unknown) {
      if (isNetworkUnreachableError(err)) {
        setBackendUnreachable(true);
        setError(BACKEND_UNREACHABLE_MESSAGE);
      } else {
        setError(err instanceof Error ? err.message : "Failed extracting sample report");
      }
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const requestFilePreviewThenExtract = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) {
      setError("Please select a file to upload.");
      return;
    }
    if (!allowCloudLlm) {
      await executeFileExtraction(false);
      return;
    }
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setBackendUnreachable(true);
      setError(API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE);
      return;
    }

    setLoading(true);
    setLoadingTarget("file");
    setError(null);
    setLastAction(() => () => executeFileExtraction(true));

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/api/extract/preview`, {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Preview generation failed");
      }
      setBackendUnreachable(false);
      const data = await response.json();
      setPendingPreview({ kind: "file", ...data });
    } catch (err: unknown) {
      if (isNetworkUnreachableError(err)) {
        setBackendUnreachable(true);
        setError(BACKEND_UNREACHABLE_MESSAGE);
      } else {
        setError(err instanceof Error ? err.message : "Preview generation failed");
      }
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const requestSamplePreviewThenExtract = async (filename: string) => {
    if (!allowCloudLlm) {
      await executeSampleExtraction(filename, false);
      return;
    }
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setBackendUnreachable(true);
      setError(API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE);
      return;
    }

    setLoading(true);
    setLoadingTarget(filename);
    setError(null);
    setLastAction(() => () => executeSampleExtraction(filename, true));

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/extract-sample/${encodeURIComponent(filename)}/preview`,
        { method: "POST" }
      );
      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || "Preview generation failed");
      }
      setBackendUnreachable(false);
      const data = await response.json();
      setPendingPreview({ kind: "sample", sampleFilename: filename, ...data });
    } catch (err: unknown) {
      if (isNetworkUnreachableError(err)) {
        setBackendUnreachable(true);
        setError(BACKEND_UNREACHABLE_MESSAGE);
      } else {
        setError(err instanceof Error ? err.message : "Preview generation failed");
      }
    } finally {
      setLoading(false);
      setLoadingTarget("");
    }
  };

  const handleConfirmSendCloud = async () => {
    const preview = pendingPreview;
    if (!preview) return;
    setPendingPreview(null);
    if (preview.kind === "file") {
      await executeFileExtraction(true);
    } else if (preview.sampleFilename) {
      await executeSampleExtraction(preview.sampleFilename, true);
    }
  };

  const handleCancelFallbackLocal = async () => {
    const preview = pendingPreview;
    if (!preview) return;
    setPendingPreview(null);
    if (preview.kind === "file") {
      await executeFileExtraction(false);
    } else if (preview.sampleFilename) {
      await executeSampleExtraction(preview.sampleFilename, false);
    }
  };

  const handleSampleSelect = () => {
    if (!selectedSample) {
      setError("Please choose a sample report from the dropdown.");
      return;
    }
    requestSamplePreviewThenExtract(selectedSample);
  };

  const handleRetryBackend = () => {
    loadSampleReports();
    if (lastAction) {
      lastAction();
    }
  };

  return (
    <div className="border border-slate-200 p-6 rounded-lg mb-8 bg-white shadow-sm">
      {backendUnreachable && (
        <div className="mb-4 p-3 rounded border border-amber-300 bg-amber-50 text-amber-900 text-xs flex flex-wrap items-center justify-between gap-2">
          <span>{API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE}</span>
          <button
            type="button"
            onClick={handleRetryBackend}
            disabled={loading}
            className="px-3 py-1 rounded bg-amber-900 text-white font-semibold hover:bg-amber-800 disabled:opacity-50"
          >
            Retry
          </button>
        </div>
      )}

      {/* What Will Be Sent Preview Gate */}
      {pendingPreview && (
        <div className="mb-6 p-4 rounded-lg border-2 border-blue-300 bg-blue-50/70 space-y-3" role="dialog" aria-label="Outbound OpenRouter payload preview">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h3 className="text-sm font-bold text-slate-900">
              What Will Be Sent to OpenRouter
            </h3>
            <span className="text-[11px] font-medium px-2 py-0.5 rounded bg-white border border-blue-200 text-blue-900">
              Kept {pendingPreview.kept_lines} of {pendingPreview.total_lines} lines
              {pendingPreview.redacted_categories.length > 0
                ? ` • Redacted: ${pendingPreview.redacted_categories.join(", ")}`
                : ""}
            </span>
          </div>
          <p className="text-xs text-slate-700 leading-relaxed">
            <strong>Exact payload notice:</strong> This preview is the exact minimized and PII-redacted text that will be sent to OpenRouter (with <code className="font-mono text-[11px]">provider.data_collection=&quot;deny&quot;</code>). Age, gender, and report date stay local as structured fields.
          </p>
          <pre className="max-h-56 overflow-auto rounded border border-slate-300 bg-white p-3 text-xs font-mono text-slate-800 whitespace-pre-wrap">
            {pendingPreview.zero_lines
              ? "[0 biomarker lines retained after minimization — Send or Cancel will run local extraction only without calling OpenRouter]"
              : pendingPreview.outbound_text}
          </pre>
          <div className="flex flex-wrap justify-end gap-2">
            <button
              type="button"
              onClick={handleCancelFallbackLocal}
              disabled={loading}
              className="px-3 py-1.5 rounded border border-slate-300 bg-white text-slate-800 text-xs font-semibold hover:bg-slate-100"
            >
              Cancel (Use Local Extraction)
            </button>
            <button
              type="button"
              onClick={handleConfirmSendCloud}
              disabled={loading}
              className="px-4 py-1.5 rounded bg-blue-600 text-white text-xs font-semibold hover:bg-blue-700"
            >
              Send
            </button>
          </div>
        </div>
      )}

      {/* 1-Click Quick Demo Banner */}
      <div className="mb-6 p-4 rounded-lg bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-blue-600 font-bold">⚡ Quick Demo:</span>
            <span className="text-xs bg-amber-100 text-amber-900 border border-amber-300 font-semibold px-2 py-0.5 rounded">
              Demo data (synthetic)
            </span>
          </div>
          <p className="text-xs text-slate-600 mt-1">
            Test the pipeline with a synthetic Indian lab panel (Metropolis Healthcare layout: impaired fasting glucose, elevated hs-CRP, and dyslipidemia).
          </p>
        </div>
        <button
          type="button"
          onClick={() => requestSamplePreviewThenExtract("02_metropolis_prediabetic.pdf")}
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
        <div className="p-3 mb-4 text-xs bg-rose-50 text-rose-700 border border-rose-200 rounded flex items-center justify-between gap-2">
          <span>{error}</span>
          <div className="flex items-center gap-2">
            {backendUnreachable && lastAction && (
              <button
                type="button"
                onClick={handleRetryBackend}
                className="px-2 py-0.5 rounded bg-rose-700 text-white font-semibold hover:bg-rose-800"
              >
                Retry
              </button>
            )}
            <button onClick={() => setError(null)} className="text-rose-500 font-bold">✕</button>
          </div>
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
            {allowCloudLlm
              ? "Preparing Preview / Extracting Biomarkers (Redacted Cloud LLM)..."
              : "Extracting Biomarkers Locally (Offline OCR + Regex Rules)..."}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            {allowCloudLlm
              ? "Minimizing lines and stripping PII locally before any OpenRouter call."
              : "Running local text extraction and physiological range checks (no data sent to cloud LLMs)."}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User File Upload */}
        <div className="border-b md:border-b-0 md:border-r border-slate-200 pb-6 md:pb-0 md:pr-6">
          <h3 className="font-semibold text-sm text-slate-800 mb-1">Option A: Upload Your PDF or Photo</h3>
          <p className="text-xs text-slate-500 mb-3">Accepts digital laboratory PDFs and phone photos (JPEG/PNG).</p>
          <form onSubmit={requestFilePreviewThenExtract} className="space-y-3">
            <input
              type="file"
              accept=".pdf,image/png,image/jpeg,image/jpg"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setPendingPreview(null);
              }}
              className="block w-full text-xs border border-slate-300 p-2 rounded cursor-pointer file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:text-xs file:bg-slate-100 file:text-slate-700"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !file}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded text-xs font-semibold hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {loading && loadingTarget === "file"
                ? "Processing File..."
                : allowCloudLlm
                ? "Preview Payload & Extract"
                : "Extract from File"}
            </button>
          </form>
        </div>

        {/* Pre-loaded Sample Selector */}
        <div>
          <div className="flex flex-wrap items-center gap-2 mb-1">
            <h3 className="font-semibold text-sm text-slate-800">Option B: Choose from 15 Sample Reports</h3>
            <span className="text-[11px] bg-amber-100 text-amber-900 border border-amber-300 font-semibold px-2 py-0.5 rounded">
              Demo data (synthetic)
            </span>
          </div>
          <p className="text-xs text-slate-500 mb-3">Includes synthetic Dr. Lal, Metropolis, Apollo, Quest layouts, plus synthetic skewed phone captures.</p>
          <div className="space-y-3">
            <select
              value={selectedSample}
              onChange={(e) => {
                setSelectedSample(e.target.value);
                setPendingPreview(null);
              }}
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
