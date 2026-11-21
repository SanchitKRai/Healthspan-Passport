"use client";

import React, { useState, useEffect } from "react";
import { SampleReportItem, ExtractionResponse } from "../types/biomarker";

interface UploadSectionProps {
  onExtractionSuccess: (data: ExtractionResponse) => void;
}

export const UploadSection: React.FC<UploadSectionProps> = ({ onExtractionSuccess }) => {
  const [file, setFile] = useState<File | null>(null);
  const [sampleReports, setSampleReports] = useState<SampleReportItem[]>([]);
  const [selectedSample, setSelectedSample] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load sample reports from backend
  useEffect(() => {
    fetch("http://localhost:8000/api/sample-reports")
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
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch("http://localhost:8000/api/extract", {
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
    }
  };

  const handleSampleSelect = async () => {
    if (!selectedSample) {
      setError("Please choose a sample report from the dropdown.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`http://localhost:8000/api/extract-sample/${selectedSample}`, {
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
    }
  };

  return (
    <div className="border p-6 rounded mb-8 bg-white">
      <h2 className="text-lg font-bold mb-4">Upload Lab Report</h2>

      {error && (
        <div className="p-3 mb-4 text-sm bg-red-50 text-red-700 border border-red-200 rounded">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* User File Upload */}
        <div className="border-r md:pr-6">
          <h3 className="font-semibold text-sm mb-2">Option A: Upload Your PDF or Photo</h3>
          <form onSubmit={handleFileUpload} className="space-y-3">
            <input
              type="file"
              accept=".pdf,image/png,image/jpeg,image/jpg"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="block w-full text-sm border p-2 rounded cursor-pointer"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !file}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Extracting..." : "Extract from File"}
            </button>
          </form>
        </div>

        {/* Pre-loaded Sample Selector */}
        <div>
          <h3 className="font-semibold text-sm mb-2">Option B: Test with Pre-Loaded Sample</h3>
          <div className="space-y-3">
            <select
              value={selectedSample}
              onChange={(e) => setSelectedSample(e.target.value)}
              className="block w-full text-sm border p-2 rounded bg-white"
              disabled={loading}
            >
              <option value="">-- Select a sample report (15 available) --</option>
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
              className="w-full bg-gray-800 text-white py-2 px-4 rounded text-sm font-medium hover:bg-gray-900 disabled:opacity-50"
            >
              {loading ? "Extracting Sample..." : "Load & Extract Sample Report"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
