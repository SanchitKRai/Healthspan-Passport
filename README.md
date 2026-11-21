# Healthspan Passport 🩺📊
> *From lab report to biological age to action plan*

Healthspan Passport transforms routine blood test reports (PDFs or phone photos) into structured preventive health intelligence.

---

## Architecture Overview

```
Healthspan-Passport/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI endpoints & CORS
│   │   ├── schemas/biomarker.py # Pydantic contract (25+ canonical biomarkers)
│   │   ├── extraction/          # pdfplumber + RapidOCR engine
│   │   └── llm/                 # OpenRouter client (Nemotron + Kimi fallback)
│   ├── scripts/
│   │   ├── generate_sample_reports.py # Generates 15 test reports & ground truth
│   │   └── bakeoff.py           # Model benchmark (Nemotron vs Kimi)
│   └── tests/                   # Complete pytest suite (12 passing tests)
├── frontend/                    # Next.js 15 + Tailwind CSS
│   └── src/
│       ├── types/biomarker.ts   # Shared TypeScript contract
│       ├── components/          # UploadSection, BiomarkerTable, PatientSummary
│       └── app/page.tsx         # Main interactive dashboard
├── data/
│   ├── sample_reports/          # 15 pre-loaded reports (8 PDFs + 7 phone photos)
│   └── ground_truth.json        # Ground-truth values for accuracy benchmarking
└── docs/
    ├── BIOMARKER_SCHEMA.md      # Frozen biomarker schema specification contract
    └── BAKEOFF_RESULTS.md       # Nemotron vs Kimi bake-off benchmark report
```

---

## Quickstart (Run in 3 Commands)

### 1. Install Dependencies
```bash
# Backend (Python 3.10+)
pip install -r backend/requirements.txt

# Frontend (Node 18+)
cd frontend && npm install && cd ..
```

### 2. Configure Environment (Optional)
```bash
# Add your OpenRouter API key for live model inference (heuristic fallback runs if unset)
export OPENROUTER_API_KEY="your-openrouter-key"
```

### 3. Run Development Servers
```bash
# Terminal 1: Backend API (FastAPI)
cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Frontend (Next.js)
cd frontend && npm run dev
```

Visit **`http://localhost:3000`** to test extraction via drag-and-drop or select any of the 15 pre-loaded sample reports.

---

## Running Verification & Tests

```bash
# Run backend test suite
cd backend && pytest tests/

# Run extraction model bake-off benchmark
python backend/scripts/bakeoff.py
```
