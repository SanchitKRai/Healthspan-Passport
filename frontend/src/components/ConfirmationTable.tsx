"use client";

import React, { useState } from "react";
import { API_BASE_URL } from "../config/api";
import { BiomarkerItem, PatientInfo, AnalysisResponse } from "../types/biomarker";

interface ConfirmationTableProps {
  initialBiomarkers: BiomarkerItem[];
  patient: PatientInfo;
  onAnalysisSuccess: (analysis: AnalysisResponse) => void;
}

export const ConfirmationTable: React.FC<ConfirmationTableProps> = ({
  initialBiomarkers,
  patient,
  onAnalysisSuccess,
}) => {
  const [biomarkers, setBiomarkers] = useState<BiomarkerItem[]>(initialBiomarkers);
  const [age, setAge] = useState<number>(patient.age || 40);
  const [gender, setGender] = useState<string>(patient.gender || "male");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleValueChange = (index: number, newVal: string) => {
    const updated = [...biomarkers];
    const num = newVal === "" ? null : parseFloat(newVal);
    updated[index] = {
      ...updated[index],
      value: isNaN(num as number) ? null : num,
      needs_review: false, // User explicitly reviewed/edited this value
    };
    setBiomarkers(updated);
  };

  const handleUnitChange = (index: number, newUnit: string) => {
    const updated = [...biomarkers];
    updated[index] = {
      ...updated[index],
      unit: newUnit,
      needs_review: false,
    };
    setBiomarkers(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!age || age <= 0 || age > 120) {
      setError("Please provide a valid chronological age (between 1 and 120).");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chronological_age: age,
          patient_gender: gender,
          biomarkers: biomarkers,
        }),
      });

      if (!response.ok) {
        const errJson = await response.json().catch(() => ({}));
        throw new Error(errJson.detail || "Analysis calculation failed");
      }

      const result: AnalysisResponse = await response.json();
      onAnalysisSuccess(result);
    } catch (err: any) {
      setError(err.message || "Failed to analyze biomarkers");
    } finally {
      setLoading(false);
    }
  };

  const reviewCount = biomarkers.filter((b) => b.needs_review || b.confidence < 0.8).length;

  return (
    <div className="border p-6 rounded bg-white mb-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-4 pb-3 border-b">
        <div>
          <h2 className="text-lg font-bold">Review & Confirm Biomarkers</h2>
          <p className="text-xs text-gray-500">
            Verify extracted values before biological age calculation. Highlighted items require confirmation.
          </p>
        </div>

        {reviewCount > 0 && (
          <div className="mt-2 md:mt-0 text-xs px-2.5 py-1 bg-amber-100 text-amber-800 rounded font-medium border border-amber-300">
            ⚠️ {reviewCount} item(s) flagged for manual review
          </div>
        )}
      </div>

      {error && (
        <div className="p-3 mb-4 text-xs bg-red-50 text-red-700 border border-red-200 rounded">
          {error}
        </div>
      )}

      {/* Patient Age & Gender Input Bar */}
      <div className="bg-gray-50 p-3 rounded mb-4 border flex flex-wrap gap-6 items-center text-sm">
        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">
            Chronological Age (Required for PhenoAge):
          </label>
          <input
            type="number"
            value={age}
            onChange={(e) => setAge(parseFloat(e.target.value) || 0)}
            className="border p-1.5 rounded w-24 text-sm bg-white"
            min={1}
            max={120}
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-700 mb-1">Sex / Gender:</label>
          <select
            value={gender}
            onChange={(e) => setGender(e.target.value)}
            className="border p-1.5 rounded text-sm bg-white"
          >
            <option value="male">Male</option>
            <option value="female">Female</option>
            <option value="other">Other</option>
          </select>
        </div>

        <div className="ml-auto">
          <button
            type="button"
            onClick={handleSubmit}
            disabled={loading}
            className="bg-blue-600 text-white px-5 py-2 rounded text-sm font-semibold hover:bg-blue-700 disabled:opacity-50"
          >
            {loading ? "Calculating..." : "Confirm & Calculate Biological Age"}
          </button>
        </div>
      </div>

      {/* Biomarker Editable Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full border border-collapse text-sm">
          <thead>
            <tr className="bg-gray-100 border-b text-left text-xs text-gray-600">
              <th className="p-2 border">Canonical ID</th>
              <th className="p-2 border">Raw Test Name</th>
              <th className="p-2 border">Value (Editable)</th>
              <th className="p-2 border">Unit (Editable)</th>
              <th className="p-2 border">Confidence</th>
              <th className="p-2 border">Status / Alert</th>
            </tr>
          </thead>
          <tbody>
            {biomarkers.map((bio, idx) => {
              const isFlagged = bio.needs_review || bio.confidence < 0.8;
              return (
                <tr
                  key={idx}
                  className={`border-b ${isFlagged ? "bg-amber-50" : idx % 2 === 1 ? "bg-gray-50" : "bg-white"}`}
                >
                  <td className="p-2 border font-mono text-xs">{bio.standard_id}</td>
                  <td className="p-2 border text-gray-800">{bio.raw_name || bio.display_name}</td>
                  <td className="p-2 border">
                    <input
                      type="number"
                      step="any"
                      value={bio.value !== null ? bio.value : ""}
                      onChange={(e) => handleValueChange(idx, e.target.value)}
                      placeholder="Enter value"
                      className={`border p-1 rounded text-sm w-28 ${
                        isFlagged ? "border-amber-400 bg-white font-semibold" : "border-gray-300"
                      }`}
                    />
                  </td>
                  <td className="p-2 border">
                    <input
                      type="text"
                      value={bio.unit}
                      onChange={(e) => handleUnitChange(idx, e.target.value)}
                      className="border p-1 rounded text-xs w-24 border-gray-300"
                    />
                  </td>
                  <td className="p-2 border text-xs">
                    {(bio.confidence * 100).toFixed(0)}%
                  </td>
                  <td className="p-2 border text-xs">
                    {isFlagged ? (
                      <span className="text-amber-800 font-semibold bg-amber-100 px-2 py-0.5 rounded">
                        Review Needed
                      </span>
                    ) : (
                      <span className="text-green-700">Confirmed</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
