"use client";

import React, { FormEvent, useState } from "react";
import { AnalysisResponse, BiomarkerItem } from "../types/biomarker";
import { API_BASE_URL } from "../config/api";

type ChatTurn = {
  role: "user" | "assistant";
  content: string;
};

interface AICompanionProps {
  analysis?: AnalysisResponse | null;
  biomarkers?: BiomarkerItem[];
}

const welcomeMessage =
  "Hi! I’m your Healthspan Passport assistant. Ask me about biomarkers, lab reports, or general health science. Upload and confirm a report to let me explain your own results. I provide education, not diagnosis or treatment.";

export const AICompanion: React.FC<AICompanionProps> = ({ analysis = null, biomarkers = [] }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatTurn[]>([
    { role: "assistant", content: welcomeMessage },
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
    const history = messages.slice(-12);

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
            confirmed: true,
          })),
          chronological_age: analysis?.chronological_age ?? null,
          phenoage: analysis?.phenoage?.phenoage ?? null,
          age_acceleration: analysis?.phenoage?.age_acceleration ?? null,
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
    <div className="fixed bottom-5 right-5 z-[100] flex flex-col items-end gap-3">
      {isOpen && (
        <section
          className="flex h-[min(620px,calc(100vh-120px))] max-h-[calc(100vh-110px)] w-[min(380px,calc(100vw-28px))] flex-col overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl"
          aria-label="Healthspan Passport AI Companion"
        >
          <div className="flex items-center justify-between bg-slate-900 px-4 py-3 text-white">
            <div className="flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-500 text-xl" aria-hidden="true">🤖</span>
              <div>
                <h2 className="text-sm font-bold">Healthspan AI</h2>
                <p className="text-[11px] text-slate-300">
                  {analysis ? "Your confirmed report is connected" : "Ask me anything about health science"}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="rounded-lg px-2 py-1 text-xl text-slate-300 hover:bg-slate-700 hover:text-white"
              aria-label="Close AI Companion"
            >
              ×
            </button>
          </div>

          <div className="flex-1 space-y-3 overflow-y-auto bg-slate-50 p-3" aria-live="polite">
            {messages.map((turn, index) => (
              <div key={index} className={`flex ${turn.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`max-w-[90%] whitespace-pre-wrap rounded-2xl px-3 py-2.5 text-sm leading-relaxed ${
                    turn.role === "user"
                      ? "rounded-br-sm bg-blue-600 text-white"
                      : "rounded-bl-sm border border-slate-200 bg-white text-slate-800 shadow-sm"
                  }`}
                >
                  {turn.content}
                </div>
              </div>
            ))}
            {loading && <p className="text-xs text-slate-500" role="status">Thinking…</p>}
          </div>

          <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white p-3">
            {error && (
              <p className="mb-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700" role="alert">
                {error}
              </p>
            )}
            <div className="flex gap-2">
              <label htmlFor="health-companion-message" className="sr-only">Your question</label>
              <input
                id="health-companion-message"
                type="text"
                value={input}
                onChange={(event) => setInput(event.target.value)}
                maxLength={2000}
                placeholder="Ask a question…"
                className="min-w-0 flex-1 rounded-xl border border-slate-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !input.trim()}
                className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Send
              </button>
            </div>
            <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
              Educational only — not a diagnosis or treatment recommendation. Seek medical care for urgent symptoms.
            </p>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="group flex items-center gap-2 rounded-full bg-blue-600 py-2 pl-2 pr-4 text-white shadow-lg ring-4 ring-blue-100 transition hover:-translate-y-0.5 hover:bg-blue-700 hover:shadow-xl focus:outline-none focus:ring-4 focus:ring-blue-200"
        aria-label={isOpen ? "Close AI Companion" : "Open AI Companion"}
        aria-expanded={isOpen}
      >
        <span className="flex h-11 w-11 items-center justify-center rounded-full bg-white text-2xl" aria-hidden="true">🤖</span>
        <span className="text-left">
          <span className="block text-sm font-bold leading-tight">Ask AI</span>
          <span className="block text-[10px] text-blue-100">Health Companion</span>
        </span>
      </button>
    </div>
  );
};

export default AICompanion;
