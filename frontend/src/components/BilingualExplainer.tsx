"use client";

import React, { useState, useEffect } from "react";

export interface ExplanationData {
  summary_en: string;
  summary_hi: string;
  key_findings_en: string[];
  key_findings_hi: string[];
  dietary_guidance_en: string[];
  dietary_guidance_hi: string[];
  questions_for_doctor_en: string[];
  questions_for_doctor_hi: string[];
  disclaimer_en: string;
  disclaimer_hi: string;
}

interface BilingualExplainerProps {
  explanation: ExplanationData | null;
  isLoading: boolean;
  onGenerate: () => void;
}

export default function BilingualExplainer({
  explanation,
  isLoading,
  onGenerate,
}: BilingualExplainerProps) {
  const [lang, setLang] = useState<"en" | "hi">("en");
  const [isSpeaking, setIsSpeaking] = useState<boolean>(false);
  const [speechSupported, setSpeechSupported] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      setSpeechSupported(true);
    }
  }, []);

  const handleToggleSpeech = () => {
    if (!speechSupported || !explanation) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();

    const summaryText = lang === "hi" ? explanation.summary_hi : explanation.summary_en;
    const findingsList = lang === "hi" ? explanation.key_findings_hi : explanation.key_findings_en;
    const textToRead = `${summaryText}. Key observations: ${findingsList.join(". ")}`;

    const utterance = new SpeechSynthesisUtterance(textToRead);
    utterance.lang = lang === "hi" ? "hi-IN" : "en-IN";
    utterance.rate = 0.95;

    // Pick appropriate voice if available
    const voices = window.speechSynthesis.getVoices();
    const targetLangPrefix = lang === "hi" ? "hi" : "en";
    const matchedVoice = voices.find((v) => v.lang.toLowerCase().startsWith(targetLangPrefix));
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }

    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    setIsSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  // Stop audio if user changes language or unmounts
  useEffect(() => {
    if (isSpeaking && typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }
  }, [lang]);

  if (!explanation) {
    return (
      <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm my-6 text-center">
        <h3 className="text-lg font-bold text-slate-900 mb-2">
          Plain-Language Bilingual Explainer & Physician Handoff
        </h3>
        <p className="text-sm text-slate-500 max-w-xl mx-auto mb-4">
          Generate an evidence-based clinical summary in English and Hindi, complete with Indian vegetarian nutrition advice and targeted questions for your next doctor consultation.
        </p>
        <button
          onClick={onGenerate}
          disabled={isLoading}
          className="bg-blue-600 hover:bg-blue-700 text-white font-medium px-4 py-2 rounded shadow-sm text-sm transition-colors disabled:opacity-50"
        >
          {isLoading ? "Generating Clinical Intelligence..." : "Generate Bilingual Summary & Doctor Questions"}
        </button>
      </div>
    );
  }

  const isHindi = lang === "hi";
  const summary = isHindi ? explanation.summary_hi : explanation.summary_en;
  const findings = isHindi ? explanation.key_findings_hi : explanation.key_findings_en;
  const dietary = isHindi ? explanation.dietary_guidance_hi : explanation.dietary_guidance_en;
  const questions = isHindi ? explanation.questions_for_doctor_hi : explanation.questions_for_doctor_en;
  const disclaimer = isHindi ? explanation.disclaimer_hi : explanation.disclaimer_en;

  return (
    <div className="bg-white border border-slate-200 rounded-lg p-6 shadow-sm my-6">
      {/* Header with Language Selector & Voice Toggle */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6 border-b border-slate-100 pb-4">
        <div>
          <h3 className="text-xl font-bold text-slate-900 flex items-center gap-2">
            <span className="text-blue-600">🩺</span>
            {isHindi ? "स्वास्थ्य विश्लेषण एवं डॉक्टर परामर्श गाइड" : "Clinical Explainer & Physician Handoff"}
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            {isHindi
              ? "आपके लैब परिणामों पर आधारित सरल भाषाई विश्लेषण और व्यक्तिगत मार्गदर्शन"
              : "Plain-language summary grounded strictly in confirmed biomarker values."}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Audio Voice Narration Button */}
          {speechSupported && (
            <button
              onClick={handleToggleSpeech}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-semibold border transition-all ${
                isSpeaking
                  ? "bg-rose-50 border-rose-300 text-rose-700 animate-pulse"
                  : "bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100"
              }`}
              title={isHindi ? "आवाज में सुनें" : "Read aloud with text-to-speech"}
            >
              <span>{isSpeaking ? "⏹" : "🔊"}</span>
              <span>{isSpeaking ? (isHindi ? "रोकें" : "Stop Audio") : isHindi ? "सुनें (आवाज)" : "Read Aloud"}</span>
            </button>
          )}

          {/* Bilingual Toggle Pills */}
          <div className="inline-flex rounded-md border border-slate-200 bg-slate-100 p-0.5 text-xs font-semibold">
            <button
              onClick={() => setLang("en")}
              className={`px-3 py-1 rounded transition-colors ${
                !isHindi
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              English
            </button>
            <button
              onClick={() => setLang("hi")}
              className={`px-3 py-1 rounded transition-colors ${
                isHindi
                  ? "bg-white text-blue-700 shadow-sm"
                  : "text-slate-600 hover:text-slate-900"
              }`}
            >
              हिंदी
            </button>
          </div>
        </div>
      </div>

      {/* Main Biological Age Summary Card */}
      <div className="p-4 rounded-lg bg-blue-50/60 border border-blue-200/70 mb-6">
        <h4 className="text-xs font-bold uppercase tracking-wider text-blue-800 mb-1">
          {isHindi ? "जैविक स्वास्थ्य निष्कर्ष" : "Biological Healthspan Synthesis"}
        </h4>
        <p className="text-sm text-slate-800 leading-relaxed font-medium">{summary}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Key Findings */}
        <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
          <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
            <span>🔍</span> {isHindi ? "मुख्य प्रयोगशाला अवलोकन" : "Key Biomarker Observations"}
          </h4>
          <ul className="space-y-2 text-xs text-slate-700">
            {findings.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-blue-600 font-bold">•</span>
                <span className="leading-snug">{item}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Indian Vegetarian Dietary Guidance */}
        <div className="p-4 rounded-lg border border-slate-200 bg-slate-50/50">
          <h4 className="text-sm font-bold text-slate-900 mb-3 flex items-center gap-2">
            <span>🥗</span> {isHindi ? "भारतीय शाकाहारी आहार मार्गदर्शन" : "Preventive Indian Nutrition Guidance"}
          </h4>
          <ul className="space-y-2 text-xs text-slate-700">
            {dietary.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2">
                <span className="text-emerald-600 font-bold">✓</span>
                <span className="leading-snug">{item}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* 3-5 Questions for Doctor */}
      <div className="p-5 rounded-lg border border-amber-200 bg-amber-50/40 mb-6">
        <div className="flex justify-between items-center mb-3">
          <h4 className="text-sm font-bold text-amber-950 flex items-center gap-2">
            <span>📋</span>
            {isHindi ? "डॉक्टर से परामर्श के लिए 5 मुख्य प्रश्न" : "3–5 Targeted Questions to Ask Your Doctor"}
          </h4>
          <span className="text-[11px] font-semibold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded">
            {isHindi ? "परामर्श तैयारी" : "Physician Handoff Ready"}
          </span>
        </div>
        <p className="text-xs text-amber-900 mb-3">
          {isHindi
            ? "अगली बार क्लिनिक या टेलीकंसल्टेशन के दौरान इन प्रश्नों को अपने डॉक्टर के साथ साझा करें:"
            : "Take these specific clinical questions to your next telemedicine or in-person physician appointment:"}
        </p>
        <ol className="space-y-2.5 text-xs text-slate-800">
          {questions.map((q, idx) => (
            <li key={idx} className="flex items-start gap-2 bg-white/80 p-2.5 rounded border border-amber-200/60 shadow-2xs">
              <span className="font-bold text-amber-800 shrink-0">{idx + 1}.</span>
              <span className="leading-relaxed">{q}</span>
            </li>
          ))}
        </ol>
      </div>

      {/* Non-Diagnostic Disclaimer */}
      <div className="text-[11px] text-slate-500 bg-slate-100/70 p-3 rounded border border-slate-200 leading-relaxed">
        <strong>{isHindi ? "महत्वपूर्ण अस्वीकरण (Disclaimer):" : "Medical Disclaimer:"}</strong> {disclaimer}
      </div>
    </div>
  );
}
