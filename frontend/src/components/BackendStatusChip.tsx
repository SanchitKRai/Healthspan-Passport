"use client";

import React, { useCallback, useEffect, useState } from "react";
import { API_BASE_URL, API_CONFIG_ERROR, BACKEND_UNREACHABLE_MESSAGE } from "../config/api";

type HealthState = "checking" | "online" | "unreachable";

export const BackendStatusChip: React.FC = () => {
  const [status, setStatus] = useState<HealthState>(API_CONFIG_ERROR ? "unreachable" : "checking");
  const [detail, setDetail] = useState<string>(API_CONFIG_ERROR || "Checking backend...");

  const checkHealth = useCallback(async () => {
    if (API_CONFIG_ERROR || !API_BASE_URL) {
      setStatus("unreachable");
      setDetail(API_CONFIG_ERROR || BACKEND_UNREACHABLE_MESSAGE);
      return;
    }

    setStatus("checking");
    setDetail("Checking / waking backend...");

    try {
      const controller = new AbortController();
      // Match the ~1 min free-tier Render cold start instead of aborting prematurely at 8s.
      const timeoutId = setTimeout(() => controller.abort(), 65000);
      const res = await fetch(`${API_BASE_URL}/api/health`, {
        method: "GET",
        signal: controller.signal,
        cache: "no-store",
      });
      clearTimeout(timeoutId);

      if (!res.ok) {
        setStatus("unreachable");
        setDetail(`${BACKEND_UNREACHABLE_MESSAGE} (${API_BASE_URL})`);
        return;
      }

      setStatus("online");
      setDetail("Backend ready");
    } catch {
      setStatus("unreachable");
      setDetail(`${BACKEND_UNREACHABLE_MESSAGE} (${API_BASE_URL})`);
    }
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const badgeStyle =
    status === "online"
      ? "bg-emerald-50 text-emerald-800 border-emerald-200"
      : status === "checking"
      ? "bg-slate-100 text-slate-700 border-slate-200"
      : "bg-amber-50 text-amber-900 border-amber-300";

  const dotStyle =
    status === "online"
      ? "bg-emerald-500"
      : status === "checking"
      ? "bg-slate-400 animate-pulse"
      : "bg-amber-500";

  return (
    <div className={`inline-flex flex-wrap items-center gap-2 px-3 py-1 rounded-full border text-xs font-medium ${badgeStyle}`}>
      <span className={`w-2 h-2 rounded-full ${dotStyle}`} aria-hidden="true" />
      <span>{detail}</span>
      {status === "unreachable" && (
        <button
          type="button"
          onClick={checkHealth}
          className="ml-1 underline font-semibold text-amber-950 hover:text-amber-700"
        >
          Retry
        </button>
      )}
    </div>
  );
};
