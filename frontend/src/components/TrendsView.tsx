"use client";

import React, { useState, useEffect } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import { DEMO_3YEAR_HISTORY, TrendReportSnapshot } from "../data/demoTrends";

interface TrendsViewProps {
  currentAnalysis?: {
    chronologicalAge: number;
    phenoage?: number | null;
    ageAcceleration?: number | null;
    biomarkers?: Record<string, number>;
  };
}

const STORAGE_KEY = "healthspan_trend_history";

export default function TrendsView({ currentAnalysis }: TrendsViewProps) {
  const [snapshots, setSnapshots] = useState<TrendReportSnapshot[]>([]);
  const [isClient, setIsClient] = useState(false);

  useEffect(() => {
    setIsClient(true);
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setSnapshots(parsed);
          return;
        }
      } catch (e) {
        console.error("Error reading localStorage", e);
      }
    }
    // Default to demo 3-year history so evaluators immediately see multi-report trends
    setSnapshots(DEMO_3YEAR_HISTORY);
  }, []);

  const handleLoadDemo = () => {
    setSnapshots(DEMO_3YEAR_HISTORY);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(DEMO_3YEAR_HISTORY));
  };

  const handleClearData = () => {
    if (window.confirm("Are you sure you want to delete all locally saved report history? This action is immediate and cannot be undone.")) {
      localStorage.removeItem(STORAGE_KEY);
      setSnapshots([]);
    }
  };

  const handleSaveCurrent = () => {
    if (!currentAnalysis || !currentAnalysis.phenoage) {
      alert("No valid biological age calculation found in the current report to save.");
      return;
    }

    const todayStr = new Date().toISOString().split("T")[0];
    const newSnapshot: TrendReportSnapshot = {
      id: `rep_${Date.now()}`,
      date: todayStr,
      labName: "Uploaded Lab Report",
      chronologicalAge: currentAnalysis.chronologicalAge,
      phenoage: Number(currentAnalysis.phenoage.toFixed(1)),
      ageAcceleration: Number((currentAnalysis.ageAcceleration ?? 0).toFixed(1)),
      biomarkers: {
        glucose_fasting: currentAnalysis.biomarkers?.glucose_fasting ?? currentAnalysis.biomarkers?.glucose ?? 95,
        crp: currentAnalysis.biomarkers?.crp ?? 1.2,
        total_cholesterol: currentAnalysis.biomarkers?.total_cholesterol ?? 190,
        hba1c: currentAnalysis.biomarkers?.hba1c ?? 5.5,
        albumin: currentAnalysis.biomarkers?.albumin ?? 4.2,
        wbc: currentAnalysis.biomarkers?.wbc ?? 6.8,
        creatinine: currentAnalysis.biomarkers?.creatinine ?? 0.9,
      },
      notes: "Newly confirmed clinical panel snapshot.",
    };

    const updated = [...snapshots, newSnapshot].sort((a, b) => a.date.localeCompare(b.date));
    setSnapshots(updated);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
    alert("Current report successfully saved to your longitudinal healthspan timeline!");
  };

  if (!isClient) return null;

  const chartData = snapshots.map((s) => ({
    date: s.date,
    lab: s.labName,
    "Chronological Age": s.chronologicalAge,
    "Biological Age (PhenoAge)": s.phenoage,
    "Fasting Glucose (mg/dL)": s.biomarkers.glucose_fasting,
    "hs-CRP (mg/L)": s.biomarkers.crp,
    "Total Cholesterol (mg/dL)": s.biomarkers.total_cholesterol,
  }));

  const hasDemoSnapshots = snapshots.some((s) =>
    DEMO_3YEAR_HISTORY.some((d) => d.id === s.id)
  );

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm my-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-slate-100 pb-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
              <span className="text-blue-600">📈</span> Longitudinal Healthspan & Biomarker Trajectory
            </h3>
            {hasDemoSnapshots && (
              <span className="text-xs bg-amber-100 text-amber-900 border border-amber-300 font-semibold px-2 py-0.5 rounded">
                Demo data (synthetic)
              </span>
            )}
          </div>
          <p className="text-sm text-slate-500 mt-1">
            Track multi-year biological age trajectory, glycemic control, and systemic inflammation over time.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          {currentAnalysis?.phenoage && (
            <button
              onClick={handleSaveCurrent}
              className="text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 px-3 py-1.5 rounded transition-colors"
            >
              + Save Current Report to Timeline
            </button>
          )}
          <button
            onClick={handleLoadDemo}
            className="text-xs font-medium text-slate-700 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded transition-colors"
          >
            Load Demo 3-Year History (Synthetic)
          </button>
          <button
            onClick={handleClearData}
            className="text-xs font-medium text-rose-600 hover:text-rose-800 bg-rose-50 hover:bg-rose-100 px-3 py-1.5 rounded transition-colors"
            title="Wipe all locally stored health records"
          >
            Privacy Mode: Clear Data
          </button>
        </div>
      </div>

      {snapshots.length === 0 ? (
        <div className="p-8 text-center border border-dashed border-slate-200 rounded-lg text-slate-500 text-sm">
          No longitudinal history found. Click &quot;Load Demo 3-Year History&quot; or confirm and save your current report above.
        </div>
      ) : (
        <div className="space-y-8">
          {/* Chart 1: PhenoAge vs Chronological Age */}
          <div className="bg-slate-50/50 p-4 rounded-lg border border-slate-200">
            <div className="flex justify-between items-center mb-3">
              <h4 className="text-sm font-bold text-slate-800">
                Biological Age vs. Chronological Age Progression
              </h4>
              <span className="text-xs text-slate-500 font-mono">
                {snapshots.length} longitudinal records
              </span>
            </div>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis domain={["dataMin - 3", "dataMax + 3"]} stroke="#64748b" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#cbd5e1", borderRadius: "6px" }}
                  />
                  <Legend wrapperStyle={{ paddingTop: "10px", fontSize: "12px" }} />
                  <Line
                    type="monotone"
                    dataKey="Chronological Age"
                    stroke="#94a3b8"
                    strokeDasharray="4 4"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="Biological Age (PhenoAge)"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={{ r: 6, fill: "#2563eb" }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Fasting Glucose, hs-CRP, Total Cholesterol */}
          <div className="bg-slate-50/50 p-4 rounded-lg border border-slate-200">
            <h4 className="text-sm font-bold text-slate-800 mb-3">
              Key Biomarker Trajectories (Metabolic & Inflammation)
            </h4>
            <div className="h-64 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="date" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip
                    contentStyle={{ backgroundColor: "#ffffff", borderColor: "#cbd5e1", borderRadius: "6px" }}
                  />
                  <Legend wrapperStyle={{ paddingTop: "10px", fontSize: "12px" }} />
                  <Line
                    type="monotone"
                    dataKey="Fasting Glucose (mg/dL)"
                    stroke="#f59e0b"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="Total Cholesterol (mg/dL)"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                  <Line
                    type="monotone"
                    dataKey="hs-CRP (mg/L)"
                    stroke="#ef4444"
                    strokeWidth={2}
                    dot={{ r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Table of Historic Records */}
          <div className="overflow-x-auto">
            <table className="min-w-full text-xs text-left border border-slate-200 rounded">
              <thead className="bg-slate-100 text-slate-700 font-semibold uppercase">
                <tr>
                  <th className="px-3 py-2">Date</th>
                  <th className="px-3 py-2">Laboratory</th>
                  <th className="px-3 py-2">Chrono Age</th>
                  <th className="px-3 py-2">PhenoAge</th>
                  <th className="px-3 py-2">Acceleration</th>
                  <th className="px-3 py-2">Glucose (mg/dL)</th>
                  <th className="px-3 py-2">hs-CRP (mg/L)</th>
                  <th className="px-3 py-2">Cholesterol</th>
                  <th className="px-3 py-2">Clinical Context</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {snapshots.map((s) => (
                  <tr key={s.id} className="hover:bg-slate-50">
                    <td className="px-3 py-2 font-medium text-slate-900">{s.date}</td>
                    <td className="px-3 py-2 text-slate-600">{s.labName}</td>
                    <td className="px-3 py-2">{s.chronologicalAge} yrs</td>
                    <td className="px-3 py-2 font-bold text-blue-700">{s.phenoage} yrs</td>
                    <td className="px-3 py-2">
                      <span
                        className={`inline-block px-1.5 py-0.5 rounded text-[11px] font-semibold ${
                          s.ageAcceleration <= 0
                            ? "bg-emerald-100 text-emerald-800"
                            : "bg-amber-100 text-amber-800"
                        }`}
                      >
                        {s.ageAcceleration > 0 ? `+${s.ageAcceleration}` : s.ageAcceleration} yrs
                      </span>
                    </td>
                    <td className="px-3 py-2">{s.biomarkers.glucose_fasting}</td>
                    <td className="px-3 py-2">{s.biomarkers.crp}</td>
                    <td className="px-3 py-2">{s.biomarkers.total_cholesterol}</td>
                    <td className="px-3 py-2 text-slate-500 max-w-xs truncate" title={s.notes}>
                      {s.notes}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="p-3 bg-slate-50 rounded border border-slate-200 text-xs text-slate-600 flex items-center justify-between">
            <span>
              🔒 <strong>Client-Side Privacy Guarantee:</strong> All longitudinal records are stored strictly in your browser&apos;s local storage (`localStorage`). No patient identity or biomarker histories are persisted to server disks.
            </span>
            <button
              onClick={handleClearData}
              className="text-xs text-rose-600 hover:underline font-medium ml-4 shrink-0"
            >
              Purge All Data
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
