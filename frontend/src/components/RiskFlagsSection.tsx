import React from "react";
import { RiskFlagItem } from "../types/biomarker";

interface RiskFlagsSectionProps {
  riskFlags: RiskFlagItem[];
}

export const RiskFlagsSection: React.FC<RiskFlagsSectionProps> = ({ riskFlags }) => {
  if (riskFlags.length === 0) {
    return null;
  }

  return (
    <div className="border rounded p-6 bg-white mb-6">
      <div className="mb-4">
        <h2 className="text-xl font-bold">Preventive Health Risk Flags</h2>
        <p className="text-xs text-gray-500">
          Multi-organ risk assessment across routine biomarkers. All insights are educational and preventive.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {riskFlags.map((flag, idx) => {
          const isElevated = flag.status === "elevated";
          const isBorderline = flag.status === "borderline";

          return (
            <div
              key={idx}
              className={`border p-4 rounded text-sm ${
                isElevated
                  ? "bg-red-50/50 border-red-200"
                  : isBorderline
                  ? "bg-amber-50/50 border-amber-200"
                  : "bg-gray-50 border-gray-200"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-semibold text-gray-900">{flag.title}</h3>
                <span
                  className={`px-2 py-0.5 rounded text-xs font-semibold uppercase ${
                    isElevated
                      ? "bg-red-100 text-red-800"
                      : isBorderline
                      ? "bg-amber-100 text-amber-800"
                      : "bg-green-100 text-green-800"
                  }`}
                >
                  {flag.status}
                </span>
              </div>

              {flag.markers.filter(Boolean).length > 0 && (
                <div className="text-xs font-mono text-gray-600 mb-2">
                  {flag.markers.filter(Boolean).join(" • ")}
                </div>
              )}

              <p className="text-xs text-gray-700 mb-3">{flag.message}</p>

              <div className="text-xs bg-white/80 p-2.5 rounded border border-gray-200">
                <strong className="text-gray-800 block mb-0.5">Preventive Recommendation:</strong>
                <span className="text-gray-600">{flag.recommendation}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
