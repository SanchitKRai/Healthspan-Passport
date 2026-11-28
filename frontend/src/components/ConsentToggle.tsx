"use client";

import React from "react";

interface ConsentToggleProps {
  allowCloudLlm: boolean;
  onChange: (allowed: boolean) => void;
}

export const ConsentToggle: React.FC<ConsentToggleProps> = ({
  allowCloudLlm,
  onChange,
}) => {
  return (
    <div
      className={`border rounded-lg p-4 mb-6 shadow-xs transition-colors ${
        allowCloudLlm
          ? "bg-blue-50/60 border-blue-200"
          : "bg-slate-50 border-slate-200"
      }`}
    >
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-bold text-slate-900">
              Cloud AI Consent (OpenRouter)
            </span>
            <span
              className={`text-[11px] font-semibold px-2 py-0.5 rounded border ${
                allowCloudLlm
                  ? "bg-blue-100 text-blue-900 border-blue-300"
                  : "bg-slate-200 text-slate-800 border-slate-300"
              }`}
            >
              {allowCloudLlm ? "Cloud AI Opted-In (Redacted)" : "Local-Only Default (Off)"}
            </span>
          </div>
          <p className="text-xs text-slate-600 leading-relaxed">
            {allowCloudLlm ? (
              <>
                Enabled: Minimized, PII-redacted biomarker lines and redacted chat messages (names, phones, emails, IDs, dates, barcodes, and addresses stripped) may be sent to OpenRouter (<code className="font-mono text-[11px]">mistralai/mistral-small-3.2-24b-instruct</code>) with <code className="font-mono text-[11px]">provider.data_collection=&quot;deny&quot;</code>. Note: the provider&apos;s own retention policy is outside our control.
              </>
            ) : (
              <>
                Off by default: Extraction uses local regex/OCR only, and the AI Companion chat will not send any questions or biomarker context to external OpenRouter models unless you opt in here.
              </>
            )}
          </p>
        </div>

        <button
          type="button"
          role="switch"
          aria-checked={allowCloudLlm}
          onClick={() => onChange(!allowCloudLlm)}
          className={`shrink-0 inline-flex items-center gap-2 px-3.5 py-2 rounded-md text-xs font-semibold border transition-colors ${
            allowCloudLlm
              ? "bg-blue-600 text-white border-blue-700 hover:bg-blue-700"
              : "bg-white text-slate-800 border-slate-300 hover:bg-slate-100"
          }`}
        >
          <span
            className={`inline-block w-3 h-3 rounded-full ${
              allowCloudLlm ? "bg-emerald-300" : "bg-slate-400"
            }`}
          />
          <span>{allowCloudLlm ? "Disable Cloud AI" : "Allow Redacted Cloud AI"}</span>
        </button>
      </div>
    </div>
  );
};

export default ConsentToggle;
