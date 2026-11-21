import React from "react";
import { BiomarkerItem } from "../types/biomarker";

interface BiomarkerTableProps {
  biomarkers: BiomarkerItem[];
}

export const BiomarkerTable: React.FC<BiomarkerTableProps> = ({ biomarkers }) => {
  if (biomarkers.length === 0) {
    return (
      <div className="border p-6 text-center text-gray-500 rounded">
        No biomarkers detected in report.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full border border-collapse text-sm">
        <thead>
          <tr className="bg-gray-100 border-b text-left">
            <th className="p-2 border">Canonical ID</th>
            <th className="p-2 border">Test Name (Raw)</th>
            <th className="p-2 border">Value</th>
            <th className="p-2 border">Unit</th>
            <th className="p-2 border">Ref Interval</th>
            <th className="p-2 border">Flag</th>
            <th className="p-2 border">Confidence</th>
            <th className="p-2 border">Status</th>
            <th className="p-2 border">Source Text</th>
          </tr>
        </thead>
        <tbody>
          {biomarkers.map((bio, idx) => {
            const isAbnormal = bio.flag === "high" || bio.flag === "low" || bio.flag === "critical";
            return (
              <tr
                key={idx}
                className={`border-b ${bio.needs_review ? "bg-amber-50" : idx % 2 === 1 ? "bg-gray-50" : "bg-white"}`}
              >
                <td className="p-2 border font-mono text-xs">{bio.standard_id}</td>
                <td className="p-2 border">{bio.raw_name || bio.display_name}</td>
                <td className={`p-2 border font-semibold ${isAbnormal ? "text-red-600" : ""}`}>
                  {bio.value !== null ? bio.value : "N/A"}
                </td>
                <td className="p-2 border text-gray-600">{bio.unit}</td>
                <td className="p-2 border text-gray-500 text-xs">
                  {bio.reference_range?.text ||
                    (bio.reference_range &&
                    bio.reference_range.low !== null &&
                    bio.reference_range.high !== null
                      ? `${bio.reference_range.low} - ${bio.reference_range.high}`
                      : "-")}
                </td>
                <td className="p-2 border">
                  <span
                    className={`px-1.5 py-0.5 text-xs rounded border ${
                      bio.flag === "normal"
                        ? "bg-green-50 text-green-700 border-green-200"
                        : bio.flag === "high" || bio.flag === "low"
                        ? "bg-red-50 text-red-700 border-red-200"
                        : "bg-gray-50 text-gray-600 border-gray-200"
                    }`}
                  >
                    {bio.flag}
                  </span>
                </td>
                <td className="p-2 border text-xs">
                  {(bio.confidence * 100).toFixed(0)}%
                </td>
                <td className="p-2 border text-xs">
                  {bio.needs_review ? (
                    <span className="text-amber-700 font-medium">⚠️ Review</span>
                  ) : (
                    <span className="text-green-700">Verified</span>
                  )}
                </td>
                <td className="p-2 border text-xs text-gray-500 max-w-xs truncate" title={bio.source_text || ""}>
                  {bio.source_text || "-"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
};
