import React from "react";
import { PhenoAgeResult } from "../types/biomarker";

interface PhenoAgeCardProps {
  phenoageResult: PhenoAgeResult;
  chronologicalAge: number;
  populationCaveat: string;
}

export const PhenoAgeCard: React.FC<PhenoAgeCardProps> = ({
  phenoageResult,
  chronologicalAge,
  populationCaveat,
}) => {
  const { is_valid, phenoage, age_acceleration, mortality_score_10yr, missing_markers, message } =
    phenoageResult;

  const isYounger = age_acceleration !== null && age_acceleration < 0;
  const isOlder = age_acceleration !== null && age_acceleration > 0;

  return (
    <div className="border rounded p-6 bg-white mb-6">
      <h2 className="text-xl font-bold mb-4">Biological Age (PhenoAge)</h2>

      {is_valid && phenoage !== null ? (
        <div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
            {/* Biological Age */}
            <div className="border p-4 rounded bg-gray-50 text-center">
              <span className="text-xs uppercase tracking-wide text-gray-500 font-semibold block">
                Biological Age
              </span>
              <span className="text-4xl font-extrabold text-blue-600 my-1 block">
                {phenoage} <span className="text-base font-normal text-gray-600">yrs</span>
              </span>
              <span className="text-xs text-gray-500">Phenotypic mortality model</span>
            </div>

            {/* Chronological Age */}
            <div className="border p-4 rounded bg-gray-50 text-center">
              <span className="text-xs uppercase tracking-wide text-gray-500 font-semibold block">
                Chronological Age
              </span>
              <span className="text-4xl font-extrabold text-gray-800 my-1 block">
                {chronologicalAge} <span className="text-base font-normal text-gray-600">yrs</span>
              </span>
              <span className="text-xs text-gray-500">From birth date</span>
            </div>

            {/* Age Acceleration Delta */}
            <div
              className={`border p-4 rounded text-center ${
                isYounger ? "bg-green-50 border-green-200" : isOlder ? "bg-red-50 border-red-200" : "bg-gray-50"
              }`}
            >
              <span className="text-xs uppercase tracking-wide text-gray-600 font-semibold block">
                Age Acceleration Delta
              </span>
              <span
                className={`text-4xl font-extrabold my-1 block ${
                  isYounger ? "text-green-700" : isOlder ? "text-red-700" : "text-gray-800"
                }`}
              >
                {age_acceleration !== null && age_acceleration > 0 ? `+${age_acceleration}` : age_acceleration}{" "}
                <span className="text-base font-normal">yrs</span>
              </span>
              <span className="text-xs font-medium">
                {isYounger
                  ? "Biologically younger than calendar age"
                  : isOlder
                  ? "Biologically older than calendar age"
                  : "Tracks calendar age"}
              </span>
            </div>
          </div>

          {mortality_score_10yr !== null && (
            <div className="text-xs text-gray-600 bg-gray-50 p-2.5 rounded border mb-4">
              <strong>Statistical 10-Year All-Cause Mortality Index:</strong> {mortality_score_10yr}%{" "}
              <span className="text-gray-400">
                (Gompertz proportional hazards baseline calibrated from NHANES III/IV)
              </span>
            </div>
          )}
        </div>
      ) : (
        /* Missing Input Alert */
        <div className="border-l-4 border-amber-500 bg-amber-50 p-4 rounded mb-6 text-sm">
          <h3 className="font-bold text-amber-800 text-base mb-1">
            ⚠️ Biological Age Cannot Be Computed
          </h3>
          <p className="text-amber-900 mb-2">{message}</p>
          {missing_markers.length > 0 && (
            <div className="text-xs text-amber-800">
              <strong>Missing Biomarker Inputs ({missing_markers.length}):</strong>{" "}
              <span className="font-mono bg-white px-2 py-0.5 rounded border border-amber-300">
                {missing_markers.join(", ")}
              </span>
            </div>
          )}
          <p className="text-xs text-amber-700 mt-2">
            * Healthspan Passport adheres strictly to clinical validation standards: we never impute or guess missing laboratory values.
          </p>
        </div>
      )}

      {/* Population Caveat Note */}
      <div className="mt-4 pt-4 border-t text-xs text-gray-500">
        <strong>Population Limitation Notice:</strong> {populationCaveat}
      </div>
    </div>
  );
};
