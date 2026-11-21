"use client";

import React, { useState, useMemo } from "react";

interface WhatIfSimulatorProps {
  chronologicalAge: number;
  initialValues?: {
    glucose_mg_dl?: number;
    crp_mg_l?: number;
    albumin_g_dl?: number;
    lymphocyte_pct?: number;
    wbc_k_ul?: number;
    rdw_pct?: number;
    creatinine_mg_dl?: number;
    mcv_fl?: number;
    alp_u_l?: number;
  };
}

// Levine 2018 Constants
const LEVINE_INTERCEPT = -19.907;
const GOMPERTZ_GAMMA = 0.0076927;
const GOMPERTZ_FACTOR = (Math.exp(120.0 * GOMPERTZ_GAMMA) - 1.0) / GOMPERTZ_GAMMA;

function calculateLevinePhenoAge(params: {
  age: number;
  albumin_g_l: number;
  creatinine_umol_l: number;
  glucose_mmol_l: number;
  crp_mg_dl: number;
  lymphocyte_pct: number;
  mcv_fl: number;
  rdw_pct: number;
  alp_u_l: number;
  wbc_10_9_l: number;
}): number {
  const lnCrp = Math.log(Math.max(0.001, params.crp_mg_dl));
  const xb =
    LEVINE_INTERCEPT +
    -0.0336 * params.albumin_g_l +
    0.0095 * params.creatinine_umol_l +
    0.1953 * params.glucose_mmol_l +
    0.0954 * lnCrp +
    -0.012 * params.lymphocyte_pct +
    0.0268 * params.mcv_fl +
    0.3306 * params.rdw_pct +
    0.00188 * params.alp_u_l +
    0.0554 * params.wbc_10_9_l +
    0.0804 * params.age;

  const term = 0.00553 * Math.exp(xb) * GOMPERTZ_FACTOR;
  return 141.50225 + Math.log(term) / 0.090165;
}

export default function WhatIfSimulator({
  chronologicalAge,
  initialValues,
}: WhatIfSimulatorProps) {
  // Baseline values
  const defaultGlucose = initialValues?.glucose_mg_dl ?? 115.0;
  const defaultCrp = initialValues?.crp_mg_l ?? 2.5;
  const defaultAlbumin = initialValues?.albumin_g_dl ?? 4.0;
  const defaultLymph = initialValues?.lymphocyte_pct ?? 28.0;
  const defaultWbc = initialValues?.wbc_k_ul ?? 7.8;
  const defaultRdw = initialValues?.rdw_pct ?? 13.5;

  const fixedCreatinine = initialValues?.creatinine_mg_dl ?? 0.95;
  const fixedMcv = initialValues?.mcv_fl ?? 89.0;
  const fixedAlp = initialValues?.alp_u_l ?? 75.0;

  // Simulator Sliders State
  const [glucose, setGlucose] = useState<number>(defaultGlucose);
  const [crp, setCrp] = useState<number>(defaultCrp);
  const [albumin, setAlbumin] = useState<number>(defaultAlbumin);
  const [lymph, setLymph] = useState<number>(defaultLymph);
  const [wbc, setWbc] = useState<number>(defaultWbc);
  const [rdw, setRdw] = useState<number>(defaultRdw);

  // Baseline PhenoAge calculation
  const baselinePhenoAge = useMemo(() => {
    return calculateLevinePhenoAge({
      age: chronologicalAge,
      albumin_g_l: defaultAlbumin * 10.0,
      creatinine_umol_l: fixedCreatinine * 88.4,
      glucose_mmol_l: defaultGlucose / 18.0182,
      crp_mg_dl: defaultCrp / 10.0,
      lymphocyte_pct: defaultLymph,
      mcv_fl: fixedMcv,
      rdw_pct: defaultRdw,
      alp_u_l: fixedAlp,
      wbc_10_9_l: defaultWbc,
    });
  }, [chronologicalAge, defaultAlbumin, fixedCreatinine, defaultGlucose, defaultCrp, defaultLymph, fixedMcv, defaultRdw, fixedAlp, defaultWbc]);

  // Simulated PhenoAge calculation
  const simulatedPhenoAge = useMemo(() => {
    return calculateLevinePhenoAge({
      age: chronologicalAge,
      albumin_g_l: albumin * 10.0,
      creatinine_umol_l: fixedCreatinine * 88.4,
      glucose_mmol_l: glucose / 18.0182,
      crp_mg_dl: crp / 10.0,
      lymphocyte_pct: lymph,
      mcv_fl: fixedMcv,
      rdw_pct: rdw,
      alp_u_l: fixedAlp,
      wbc_10_9_l: wbc,
    });
  }, [chronologicalAge, albumin, fixedCreatinine, glucose, crp, lymph, fixedMcv, rdw, fixedAlp, wbc]);

  const deltaYears = simulatedPhenoAge - baselinePhenoAge;
  const simulatedAcceleration = simulatedPhenoAge - chronologicalAge;

  const handleReset = () => {
    setGlucose(defaultGlucose);
    setCrp(defaultCrp);
    setAlbumin(defaultAlbumin);
    setLymph(defaultLymph);
    setWbc(defaultWbc);
    setRdw(defaultRdw);
  };

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm my-6">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span className="text-blue-600">⚡</span> Interactive What-If Longevity Simulator
          </h3>
          <p className="text-sm text-slate-500 mt-1">
            Simulate how targeted lifestyle interventions (improving glycemic control, lowering inflammation) change your PhenoAge in real time.
          </p>
        </div>
        <button
          onClick={handleReset}
          className="text-xs font-medium text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-3 py-1.5 rounded transition-colors"
        >
          Reset to Baseline
        </button>
      </div>

      {/* Simulator Output Summary Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 rounded-lg bg-slate-50 border border-slate-200 mb-6">
        <div className="text-center p-2">
          <div className="text-xs uppercase font-semibold text-slate-500">Current Baseline</div>
          <div className="text-2xl font-bold text-slate-800 mt-1">
            {baselinePhenoAge.toFixed(1)} <span className="text-sm font-normal text-slate-500">yrs</span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5">Chronological: {chronologicalAge} yrs</div>
        </div>

        <div className="text-center p-2 border-y md:border-y-0 md:border-x border-slate-200">
          <div className="text-xs uppercase font-semibold text-slate-500">Simulated PhenoAge</div>
          <div className="text-2xl font-bold text-blue-700 mt-1">
            {simulatedPhenoAge.toFixed(1)} <span className="text-sm font-normal text-slate-500">yrs</span>
          </div>
          <div className="text-xs text-slate-500 mt-0.5">
            Accel: {simulatedAcceleration > 0 ? `+${simulatedAcceleration.toFixed(1)}` : simulatedAcceleration.toFixed(1)} yrs
          </div>
        </div>

        <div className="text-center p-2">
          <div className="text-xs uppercase font-semibold text-slate-500">Longevity Impact (Delta)</div>
          <div
            className={`text-2xl font-bold mt-1 ${
              deltaYears < -0.1
                ? "text-emerald-600"
                : deltaYears > 0.1
                ? "text-amber-600"
                : "text-slate-700"
            }`}
          >
            {deltaYears > 0 ? `+${deltaYears.toFixed(1)}` : deltaYears.toFixed(1)}{" "}
            <span className="text-sm font-normal">yrs</span>
          </div>
          <div className="text-xs mt-0.5 font-medium">
            {deltaYears < -0.1 ? (
              <span className="text-emerald-700">✓ Biological Rejuvenation</span>
            ) : deltaYears > 0.1 ? (
              <span className="text-amber-700">⚠ Accelerated Risk</span>
            ) : (
              <span className="text-slate-500">No shift from baseline</span>
            )}
          </div>
        </div>
      </div>

      {/* Sliders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Fasting Glucose */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">Fasting Glucose</span>
            <span className="font-bold text-blue-700">{glucose} mg/dL</span>
          </div>
          <input
            type="range"
            min={70}
            max={180}
            step={1}
            value={glucose}
            onChange={(e) => setGlucose(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Optimal (70-99)</span>
            <span>Pre-diabetic (100-125)</span>
            <span>Elevated (&gt;126)</span>
          </div>
        </div>

        {/* hs-CRP */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">hs-CRP (Systemic Inflammation)</span>
            <span className="font-bold text-blue-700">{crp.toFixed(1)} mg/L</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={10.0}
            step={0.1}
            value={crp}
            onChange={(e) => setCrp(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Low Risk (&lt;1.0)</span>
            <span>Average (1.0-3.0)</span>
            <span>High Risk (&gt;3.0)</span>
          </div>
        </div>

        {/* Serum Albumin */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">Serum Albumin (Protein/Liver)</span>
            <span className="font-bold text-blue-700">{albumin.toFixed(1)} g/dL</span>
          </div>
          <input
            type="range"
            min={3.0}
            max={5.5}
            step={0.1}
            value={albumin}
            onChange={(e) => setAlbumin(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Low (&lt;3.5)</span>
            <span>Optimal (4.0-5.0)</span>
            <span>High (&gt;5.0)</span>
          </div>
        </div>

        {/* Lymphocyte % */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">Lymphocyte % (Immune Resilience)</span>
            <span className="font-bold text-blue-700">{lymph.toFixed(0)} %</span>
          </div>
          <input
            type="range"
            min={15}
            max={50}
            step={1}
            value={lymph}
            onChange={(e) => setLymph(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Low (&lt;20%)</span>
            <span>Optimal (25-40%)</span>
            <span>High (&gt;40%)</span>
          </div>
        </div>

        {/* White Blood Cell Count */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">WBC Count (Immune Activation)</span>
            <span className="font-bold text-blue-700">{wbc.toFixed(1)} 10³/µL</span>
          </div>
          <input
            type="range"
            min={3.5}
            max={15.0}
            step={0.1}
            value={wbc}
            onChange={(e) => setWbc(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Low (&lt;4.0)</span>
            <span>Optimal (4.5-8.0)</span>
            <span>Elevated (&gt;10.0)</span>
          </div>
        </div>

        {/* RDW */}
        <div className="p-3 border border-slate-100 rounded-md bg-white">
          <div className="flex justify-between text-sm font-medium mb-1">
            <span className="text-slate-800">RDW (Red Cell Distribution Width)</span>
            <span className="font-bold text-blue-700">{rdw.toFixed(1)} %</span>
          </div>
          <input
            type="range"
            min={11.0}
            max={18.0}
            step={0.1}
            value={rdw}
            onChange={(e) => setRdw(Number(e.target.value))}
            className="w-full accent-blue-600 cursor-pointer"
          />
          <div className="flex justify-between text-[11px] text-slate-400 mt-1">
            <span>Optimal (11.5-13.5)</span>
            <span>Mild Anisocytosis (13.6-15.0)</span>
            <span>Elevated (&gt;15.0)</span>
          </div>
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-50/50 rounded border border-blue-100 text-xs text-blue-800 flex items-start gap-2">
        <span>ℹ️</span>
        <span>
          <strong>Scientific Model:</strong> Simulations execute the exact peer-reviewed Gompertz proportional hazards formula (Levine et al., 2018). Modifying glycemic control and reducing systemic inflammation via diet and aerobic training produces significant biological age shifts.
        </span>
      </div>
    </div>
  );
}
