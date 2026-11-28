"use client";

import React, { useState } from "react";
import { API_BASE_URL } from "../config/api";
import {
  BiomarkerItem,
  CanonicalBiomarker,
  PatientInfo,
  AnalysisResponse,
} from "../types/biomarker";

interface ConfirmationTableProps {
  initialBiomarkers: BiomarkerItem[];
  patient: PatientInfo;
  onAnalysisSuccess: (analysis: AnalysisResponse) => void;
}

interface ManualPanelSpec {
  standard_id: CanonicalBiomarker;
  display_name: string;
  default_unit: string;
  is_phenoage_core: boolean;
}

const MANUAL_PANEL_OPTIONS: ManualPanelSpec[] = [
  // 9 Core Levine (2018) PhenoAge Biomarkers
  { standard_id: CanonicalBiomarker.ALBUMIN, display_name: "Serum Albumin", default_unit: "g/dL", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.CREATININE, display_name: "Serum Creatinine", default_unit: "mg/dL", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.GLUCOSE_FASTING, display_name: "Fasting Blood Glucose", default_unit: "mg/dL", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.CRP, display_name: "C-Reactive Protein (hs-CRP)", default_unit: "mg/L", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.LYMPHOCYTE_PCT, display_name: "Lymphocytes (%)", default_unit: "%", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.MCV, display_name: "Mean Corpuscular Volume (MCV)", default_unit: "fL", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.RDW, display_name: "Red Cell Distribution Width (RDW)", default_unit: "%", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.ALP, display_name: "Alkaline Phosphatase (ALP)", default_unit: "U/L", is_phenoage_core: true },
  { standard_id: CanonicalBiomarker.WBC, display_name: "Total WBC / Leukocyte Count", default_unit: "10^3/uL", is_phenoage_core: true },
  // Common Routine Panel
  { standard_id: CanonicalBiomarker.HEMOGLOBIN, display_name: "Hemoglobin", default_unit: "g/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.PLATELETS, display_name: "Platelet Count", default_unit: "10^3/uL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.HBA1C, display_name: "HbA1c", default_unit: "%", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.CHOLESTEROL_TOTAL, display_name: "Total Cholesterol", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.CHOLESTEROL_HDL, display_name: "HDL Cholesterol", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.CHOLESTEROL_LDL, display_name: "LDL Cholesterol", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.TRIGLYCERIDES, display_name: "Triglycerides", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.BILIRUBIN_TOTAL, display_name: "Total Bilirubin", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.AST_SGOT, display_name: "AST / SGOT", default_unit: "U/L", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.ALT_SGPT, display_name: "ALT / SGPT", default_unit: "U/L", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.BUN, display_name: "Blood Urea Nitrogen (BUN)", default_unit: "mg/dL", is_phenoage_core: false },
  { standard_id: CanonicalBiomarker.URIC_ACID, display_name: "Uric Acid", default_unit: "mg/dL", is_phenoage_core: false },
];

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

  const [selectedManualId, setSelectedManualId] = useState<CanonicalBiomarker>(
    CanonicalBiomarker.ALBUMIN
  );
  const [manualValue, setManualValue] = useState<string>("");
  const [manualUnit, setManualUnit] = useState<string>("g/dL");

  const lowConfidenceOrFlagged = biomarkers.some(
    (b) => b.needs_review || b.confidence < 0.8
  );
  const showUnreliableNotice =
    initialBiomarkers.length < 3 ||
    initialBiomarkers.some((b) => b.needs_review || b.confidence < 0.8);

  const handleValueChange = (index: number, newVal: string) => {
    const updated = [...biomarkers];
    const num = newVal === "" ? null : parseFloat(newVal);
    const validNum = num !== null && !isNaN(num) ? num : null;
    updated[index] = {
      ...updated[index],
      value: validNum,
      confidence: validNum !== null ? 1.0 : updated[index].confidence,
      needs_review: validNum === null,
    };
    setBiomarkers(updated);
  };

  const handleUnitChange = (index: number, newUnit: string) => {
    const updated = [...biomarkers];
    updated[index] = {
      ...updated[index],
      unit: newUnit,
      confidence: updated[index].value !== null ? 1.0 : updated[index].confidence,
      needs_review: updated[index].value === null,
    };
    setBiomarkers(updated);
  };

  const handleConfirmRow = (index: number) => {
    const updated = [...biomarkers];
    if (updated[index].value === null) {
      setError("Enter a numeric value before confirming a row.");
      return;
    }
    updated[index] = {
      ...updated[index],
      confidence: 1.0,
      needs_review: false,
    };
    setBiomarkers(updated);
    setError(null);
  };

  const handleRemoveRow = (index: number) => {
    setBiomarkers(biomarkers.filter((_, i) => i !== index));
  };

  const handleManualMarkerSelect = (idStr: string) => {
    const chosen = idStr as CanonicalBiomarker;
    setSelectedManualId(chosen);
    const spec = MANUAL_PANEL_OPTIONS.find((o) => o.standard_id === chosen);
    if (spec) {
      setManualUnit(spec.default_unit);
    }
  };

  const handleAddManualBiomarker = () => {
    const spec = MANUAL_PANEL_OPTIONS.find((o) => o.standard_id === selectedManualId);
    if (!spec) return;
    const parsed = manualValue.trim() === "" ? null : parseFloat(manualValue);
    if (parsed === null || isNaN(parsed)) {
      setError("Please enter a valid numeric value for the manual biomarker.");
      return;
    }

    const newItem: BiomarkerItem = {
      standard_id: spec.standard_id,
      display_name: spec.display_name,
      raw_name: `${spec.display_name} (manual)`,
      value: parsed,
      unit: manualUnit.trim() || spec.default_unit,
      standard_unit: spec.default_unit,
      confidence: 1.0,
      flag: "normal",
      needs_review: false,
      source_text: "Manual entry",
    };

    const existingIdx = biomarkers.findIndex((b) => b.standard_id === spec.standard_id);
    if (existingIdx >= 0) {
      const updated = [...biomarkers];
      updated[existingIdx] = newItem;
      setBiomarkers(updated);
    } else {
      setBiomarkers([...biomarkers, newItem]);
    }
    setManualValue("");
    setError(null);
  };

  const handlePopulatePhenoAgeRows = () => {
    const present = new Set(biomarkers.map((b) => b.standard_id));
    const additions: BiomarkerItem[] = MANUAL_PANEL_OPTIONS.filter(
      (opt) => opt.is_phenoage_core && !present.has(opt.standard_id)
    ).map((opt) => ({
      standard_id: opt.standard_id,
      display_name: opt.display_name,
      raw_name: `${opt.display_name} (manual)`,
      value: null,
      unit: opt.default_unit,
      standard_unit: opt.default_unit,
      confidence: 0.0,
      flag: "unknown",
      needs_review: true,
      source_text: "Manual entry required",
    }));

    if (additions.length > 0) {
      setBiomarkers([...biomarkers, ...additions]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!age || age <= 0 || age > 120) {
      setError("Please provide a valid chronological age (between 1 and 120).");
      return;
    }

    if (lowConfidenceOrFlagged) {
      setError(
        "Unconfirmed items remain flagged for review. Confirm, edit, or remove every flagged row before calculating PhenoAge."
      );
      return;
    }

    const confirmedBiomarkers = biomarkers.filter(
      (b) => !b.needs_review && b.confidence >= 0.8 && b.value !== null
    );
    if (confirmedBiomarkers.length === 0) {
      setError("Add or confirm at least one numeric biomarker before running analysis.");
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
          biomarkers: confirmedBiomarkers,
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
          <h2 className="text-lg font-bold">Review &amp; Confirm Biomarkers</h2>
          <p className="text-xs text-gray-500">
            Verify extracted values before biological age calculation. PhenoAge is never computed from unconfirmed values.
          </p>
        </div>

        {reviewCount > 0 && (
          <div className="mt-2 md:mt-0 text-xs px-2.5 py-1 bg-amber-100 text-amber-800 rounded font-medium border border-amber-300">
            {reviewCount} item(s) flagged for manual review
          </div>
        )}
      </div>

      {showUnreliableNotice && (
        <div className="mb-4 p-3 rounded border border-amber-300 bg-amber-50 text-amber-900 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <strong>We couldn&apos;t read this reliably.</strong>{" "}
            {initialBiomarkers.length < 3
              ? `Only ${initialBiomarkers.length} biomarker(s) were extracted.`
              : "Some extracted rows have low confidence or split OCR ambiguity."}{" "}
            Please confirm highlighted rows or enter values manually below before computing PhenoAge.
          </div>
          <button
            type="button"
            onClick={handlePopulatePhenoAgeRows}
            className="shrink-0 px-3 py-1.5 rounded bg-amber-900 text-white font-semibold hover:bg-amber-800"
          >
            Populate Missing 9 PhenoAge Rows
          </button>
        </div>
      )}

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
      <div className="overflow-x-auto mb-5">
        <table className="min-w-full border border-collapse text-sm">
          <thead>
            <tr className="bg-gray-100 border-b text-left text-xs text-gray-600">
              <th className="p-2 border">Canonical ID</th>
              <th className="p-2 border">Raw Test Name</th>
              <th className="p-2 border">Value (Editable)</th>
              <th className="p-2 border">Unit (Editable)</th>
              <th className="p-2 border">Confidence</th>
              <th className="p-2 border">Status / Actions</th>
            </tr>
          </thead>
          <tbody>
            {biomarkers.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-4 text-center text-xs text-gray-500">
                  No biomarkers extracted yet. Use &quot;Populate Missing 9 PhenoAge Rows&quot; or add values manually below.
                </td>
              </tr>
            ) : (
              biomarkers.map((bio, idx) => {
                const isFlagged = bio.needs_review || bio.confidence < 0.8;
                return (
                  <tr
                    key={`${bio.standard_id}-${idx}`}
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
                      <div className="flex flex-wrap items-center gap-2">
                        {isFlagged ? (
                          <>
                            <span className="text-amber-800 font-semibold bg-amber-100 px-2 py-0.5 rounded">
                              Review Needed
                            </span>
                            {bio.value !== null && (
                              <button
                                type="button"
                                onClick={() => handleConfirmRow(idx)}
                                className="px-2 py-0.5 rounded bg-blue-600 text-white font-semibold hover:bg-blue-700"
                              >
                                Confirm
                              </button>
                            )}
                          </>
                        ) : (
                          <span className="text-green-700 font-medium">Confirmed</span>
                        )}
                        <button
                          type="button"
                          onClick={() => handleRemoveRow(idx)}
                          className="text-gray-500 hover:text-rose-600 ml-auto"
                          aria-label={`Remove ${bio.display_name}`}
                        >
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Integrated Manual-Entry Bar for PhenoAge & Common Panel */}
      <div className="border rounded p-4 bg-slate-50 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="text-xs font-bold text-slate-800 uppercase tracking-wide">
              Manual Entry (9 PhenoAge Core + Common Panel)
            </h3>
            <p className="text-[11px] text-slate-600">
              Add or update any unread marker directly into the confirmation table above.
            </p>
          </div>
          <button
            type="button"
            onClick={handlePopulatePhenoAgeRows}
            className="text-xs px-2.5 py-1 rounded border border-slate-300 bg-white text-slate-700 hover:bg-slate-100 font-medium"
          >
            + Add Missing 9 PhenoAge Rows
          </button>
        </div>

        <div className="flex flex-wrap items-end gap-3 text-xs">
          <div className="min-w-[220px] flex-1">
            <label className="block font-semibold text-slate-700 mb-1">Biomarker</label>
            <select
              value={selectedManualId}
              onChange={(e) => handleManualMarkerSelect(e.target.value)}
              className="w-full border border-slate-300 rounded p-1.5 bg-white text-slate-800"
            >
              <optgroup label="Core PhenoAge (9 Required)">
                {MANUAL_PANEL_OPTIONS.filter((o) => o.is_phenoage_core).map((opt) => (
                  <option key={opt.standard_id} value={opt.standard_id}>
                    {opt.display_name} ({opt.default_unit})
                  </option>
                ))}
              </optgroup>
              <optgroup label="Common Routine Panel">
                {MANUAL_PANEL_OPTIONS.filter((o) => !o.is_phenoage_core).map((opt) => (
                  <option key={opt.standard_id} value={opt.standard_id}>
                    {opt.display_name} ({opt.default_unit})
                  </option>
                ))}
              </optgroup>
            </select>
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Value</label>
            <input
              type="number"
              step="any"
              value={manualValue}
              onChange={(e) => setManualValue(e.target.value)}
              placeholder="e.g. 4.5"
              className="border border-slate-300 rounded p-1.5 w-28 bg-white"
            />
          </div>

          <div>
            <label className="block font-semibold text-slate-700 mb-1">Unit</label>
            <input
              type="text"
              value={manualUnit}
              onChange={(e) => setManualUnit(e.target.value)}
              className="border border-slate-300 rounded p-1.5 w-24 bg-white"
            />
          </div>

          <button
            type="button"
            onClick={handleAddManualBiomarker}
            className="px-4 py-1.5 rounded bg-slate-800 text-white font-semibold hover:bg-slate-900"
          >
            Add / Update Row
          </button>
        </div>
      </div>
    </div>
  );
};
