export interface TrendReportSnapshot {
  id: string;
  date: string;
  labName: string;
  chronologicalAge: number;
  phenoage: number;
  ageAcceleration: number;
  biomarkers: {
    glucose_fasting: number; // mg/dL
    crp: number;             // mg/L
    total_cholesterol: number; // mg/dL
    hba1c: number;           // %
    albumin: number;         // g/dL
    wbc: number;             // 10^3/µL
    creatinine: number;      // mg/dL
  };
  notes: string;
}

export const DEMO_3YEAR_HISTORY: TrendReportSnapshot[] = [
  {
    id: "hist_2024_03",
    date: "2024-03-15",
    labName: "Dr. Lal PathLabs",
    chronologicalAge: 46.0,
    phenoage: 51.4,
    ageAcceleration: +5.4,
    biomarkers: {
      glucose_fasting: 122.0,
      crp: 3.4,
      total_cholesterol: 242.0,
      hba1c: 6.2,
      albumin: 3.9,
      wbc: 8.9,
      creatinine: 1.05,
    },
    notes: "Baseline checkup: Impaired fasting glucose, elevated hs-CRP, metabolic syndrome indicators.",
  },
  {
    id: "hist_2025_02",
    date: "2025-02-10",
    labName: "Metropolis Healthcare",
    chronologicalAge: 47.0,
    phenoage: 47.8,
    ageAcceleration: +0.8,
    biomarkers: {
      glucose_fasting: 104.0,
      crp: 1.6,
      total_cholesterol: 208.0,
      hba1c: 5.7,
      albumin: 4.2,
      wbc: 7.2,
      creatinine: 0.95,
    },
    notes: "Year 1 follow-up: Adopted low-glycemic Indian diet (millets/dal substitution), regular resistance exercise.",
  },
  {
    id: "hist_2026_01",
    date: "2026-01-20",
    labName: "Apollo Diagnostics",
    chronologicalAge: 48.0,
    phenoage: 44.1,
    ageAcceleration: -3.9,
    biomarkers: {
      glucose_fasting: 91.0,
      crp: 0.7,
      total_cholesterol: 178.0,
      hba1c: 5.3,
      albumin: 4.5,
      wbc: 5.9,
      creatinine: 0.88,
    },
    notes: "Year 2 follow-up: Sustained cardiometabolic optimization; biological age is now 3.9 years younger than chronological age.",
  },
];
