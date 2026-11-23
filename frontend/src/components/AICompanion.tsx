"use client";

import React, { FormEvent, useState } from "react";
import { AnalysisResponse, BiomarkerItem } from "../types/biomarker";
import { API_BASE_URL } from "../config/api";

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

interface AICompanionProps {
  analysis: AnalysisResponse;
  biomarkers: BiomarkerItem[];
}

export const AICompanion: React.FC<AICompanionProps> = ({ analysis, biomarkers }) => {
  const [messages, setMessages] = useState<ChatTurn[]>([
    {
      role: "assistant",
      content:
        "Hi! I’m your Healthspan Passport AI Companion. Ask me to explain a confirmed biomarker, its lab reference interval, or a term in your report. I provide educational information, not a diagnosis or treatment plan.",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const message = input.trim();
    if (!message || loading) return;

    setError(null);
    setLoading(true);

    const history = messages
      .filter((turn) => turn.role === "user" || turn.role === "assistant")
      .slice(-12);

    try {
      const response = await fetch(`${API_BASE_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message,
          history,
          biomarkers: biomarkers.map((biomarker) => ({
            display_name: biomarker.display_name,
            value: biomarker.value,
            unit: biomarker.standard_unit || biomarker.unit,
            reference_range: biomarker.reference_range?.text ?? null,
            flag: biomarker.flag,
            // The user has reviewed and submitted this analysis through Confirm & Calculate.
            confirmed: true,
          })),
          chronological_age: analysis.chronological_age,
          phenoage: analysis.phenoage.phenoage,
          age_acceleration: analysis.phenoage.age_acceleration,
        }),
      });

      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.detail || "The AI assistant is temporarily unavailable. Please try again.");
      }
      if (typeof data.reply !== "string" || !data.reply.trim()) {
        throw new Error("The assistant returned an empty answer. Please try again.");
      }

      setMessages((current) => [
        ...current,
        { role: "user", content: message },
        { role: "assistant", content: data.reply.trim() },
      ]);
      setInput("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="rounded-xl border border-slate-200 bg-white shadow-sm overflow-hidden">
      <div className="border-b border-slate-200 bg-slate-50 px-5 py-4">
        <div className="flex items-center gap-2">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-100 text-blue-700" aria-hidden="true">
            ✦
          </span>
          <div>
            <h2 className="text-lg font-bold text-slate-900">AI Health Companion</h2>
            <p className="text-xs text-slate-500">Ask questions about your confirmed report data</p>
          </div>
        </div>
      </div>

      <div className="max-h-96 space-y-3 overflow-y-auto p-4" aria-live="polite">
        {messages.map((turn, index) => (
          <div
            key={index}
            className={`flex ${turn.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[90%] whitespace-pre-wrap rounded-xl px-4 py-3 text-sm leading-relaxed ${
                turn.role === "user"
                  ? "bg-blue-600 text-white"
                  : "border border-slate-200 bg-slate-50 text-slate-800"
              }`}
            >
              {turn.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="text-xs text-slate-500" role="status">
            AI Companion is preparing an explanation…
          </div>
        )}
      </div>

      <form onSubmit={handleSubmit} className="border-t border-slate-200 p-4">
        {error && (
          <p className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
            {error}
          </p>
        )}
        <div className="flex flex-col gap-2 sm:flex-row">
          <label htmlFor="health-companion-message" className="sr-only">
            Ask the AI Health Companion a question
          </label>
          <input
            id="health-companion-message"
            type="text"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            maxLength={2000}
            placeholder="e.g. What does my hemoglobin result mean?"
            className="min-w-0 flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Thinking…" : "Send"}
          </button>
        </div>
        <p className="mt-2 text-[11px] leading-relaxed text-slate-500">
          Educational use only. This assistant does not diagnose conditions or recommend treatment. For urgent or severe symptoms, seek medical care.
        </p>
      </form>
    </section>
  );
};

export default AICompanion;
