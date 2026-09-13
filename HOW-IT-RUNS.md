# How the Project Runs — Architecture & Data Flow

> A plain-English explanation of what happens when you run the app,
> how each component connects, and what each file does.
> Reference this when demoing or explaining the project to judges.

---

## 1. The Big Picture

```
You (browser)
     │
     ▼
Streamlit UI  (http://localhost:8501)
     │  HTTP POST
     ▼
FastAPI backend  (http://localhost:8000)
     │
     ├──► openFDA FAERS API  ──► real FDA adverse event data
     │         (or local fallback if API unavailable)
     │
     ├──► PRR Calculator  ──► flags drug-event signals
     │
     ├──► ICH M4 CTD Checklist  ──► checks dossier completeness
     │
     └──► IBM watsonx.ai  ──► AI-generated rationale & gap reports
```

Both the backend and frontend start together with one command:
```powershell
python run.py
```

---

## 2. What Starts When You Run `python run.py`

```
run.py
├── Detects .venv → re-launches inside it automatically
├── Checks src/.env exists and WATSONX_API_KEY is set
├── Starts: uvicorn backend.main:app --port 8000   [Terminal 1 equivalent]
├── Waits until :8000 accepts connections
├── Starts: streamlit run frontend/app.py --port 8501  [Terminal 2 equivalent]
├── Waits until :8501 accepts connections
├── Opens http://localhost:8501 in your browser
└── Streams [API] and [UI] logs to console
    Ctrl+C → stops both servers cleanly
```

---

## 3. Mode 1 — Signal Detection: Step by Step

**User action:** Types `aspirin` in the drug name box, clicks "Run Signal Analysis"

```
Step 1  Frontend (app.py)
        POST http://localhost:8000/signals
        Body: {"drug_name": "aspirin", "limit": 1000}

Step 2  Backend (main.py) receives request
        Calls: fetch_faers_reports("aspirin", 1000)

Step 3  Data layer (openfda_client.py)
        GET https://api.fda.gov/drug/event.json
            ?search=patient.drug.medicinalproduct:ASPIRIN
            &limit=1000
            &api_key=<OPENFDA_API_KEY>
        → Returns up to 1000 FAERS report JSON objects
        → If API returns 403 or network fails:
            loads src/data/sample_faers.json instead (101 records)
            sets fallback_used = True

Step 4  PRR Calculator (prr.py)
        For each report, extract (drug_name, adverse_event_term) pairs
        Build counts: a, b, c, d per pair
        Compute PRR = (a / (a+b)) / (c / (c+d))
        Filter: keep only PRR >= 2.0 AND count >= 3
        Sort descending by PRR
        → Returns list of flagged signals

Step 5  LLM (client.py + prompts.py)
        Top 10 signals → build_signal_rationale_prompt()
        POST to IBM watsonx.ai:
            Model: ibm/granite-13b-instruct-v2
            Prompt: "These drug-event pairs are flagged. Explain each..."
        → Returns numbered list of plain-language rationales
        → If WATSONX_API_KEY not set: returns stub notice instead

Step 6  Backend returns JSON:
        {
          "drug_name": "aspirin",
          "total_reports": 847,
          "fallback_used": false,
          "signals": [
            {"drug": "ASPIRIN", "adverse_event": "Gastrointestinal haemorrhage",
             "prr": 4.73, "report_count": 62, "rationale": "Aspirin inhibits COX-1..."}
          ]
        }

Step 7  Frontend (app.py) renders:
        ├── Metric cards: reports fetched / signals flagged / threshold
        ├── Blue banner if fallback was used
        └── Expandable rows per signal:
            🔴 PRR≥5  🟡 PRR 2-5  🟢 at threshold
            Each row shows: PRR value, count, AI rationale
```

---

## 4. Mode 2 — Submission Readiness: Step by Step

**User action:** Pastes CTD section list (or uploads .txt file), clicks "Check Readiness"

```
Step 1  Frontend (app.py)
        POST http://localhost:8000/readiness
        Body: {"outline": ["1.0 Cover letter", "2.3 Quality Overall Summary", ...]}

Step 2  Backend (main.py) receives request
        Calls: check_readiness(outline)

Step 3  Readiness Checker (readiness.py)
        Loads ICH M4 checklist from ctd_checklist.py (45 required sections)
        For each required section:
            Normalise to lowercase
            Fuzzy-match against every user line (thefuzz token_sort_ratio >= 72)
            Mark: PRESENT or MISSING
        Compute per-module score = present/required * 100
        Compute overall score

Step 4  LLM (client.py + prompts.py)
        Missing sections per module → build_gap_report_prompt()
        POST to IBM watsonx.ai:
            Model: ibm/granite-13b-instruct-v2
            Prompt: "These ICH M4 sections are missing. Write a regulatory gap report..."
        → Returns 3-5 paragraph prose gap report
        → If WATSONX_API_KEY not set: returns stub notice

Step 5  Backend returns JSON:
        {
          "overall_score": 42.1,
          "modules": [
            {"module": "Module 3", "module_name": "Quality",
             "score": 42.9, "present": 6, "required": 14,
             "missing": ["3.2.S.7 — Drug substance stability", ...]}
          ],
          "gap_report": "The submitted dossier is missing critical stability..."
        }

Step 6  Frontend (app.py) renders:
        ├── Overall score with colour: green≥80% / yellow≥50% / red<50%
        ├── Progress bar (0-100%)
        ├── Per-module section:
        │   ├── 🟢🟡🔴 colour-coded progress bars
        │   ├── Score % and present/required count
        │   └── Expandable list of missing sections
        └── AI Regulatory Gap Report (prose from Granite)
```

---

## 5. File Roles — What Each File Does

### Entry Points
| File | Role |
|---|---|
| `run.py` | Single-command launcher — starts both servers, handles venv detection, port checks, browser open, clean shutdown |
| `run.bat` | Windows double-click shortcut → calls `run.py` |
| `run.sh` | macOS/Linux shortcut → calls `run.py` |

### Backend (`src/backend/`)
| File | Role |
|---|---|
| `main.py` | FastAPI app. Defines 3 routes: `GET /health`, `POST /signals`, `POST /readiness`. Orchestrates calls to data, PRR, readiness, and LLM layers. |
| `prr.py` | Pure computation. Takes list of FAERS report dicts → returns ranked list of flagged (drug, event, PRR, count) signals. |
| `readiness.py` | Takes list of section title strings → loads checklist → fuzzy-matches → returns per-module scores and missing sections list. |
| `models.py` | Pydantic schemas. Defines the exact shape of every API request and response. Powers the Swagger `/docs` UI. |

### Data Layer (`src/data/`)
| File | Role |
|---|---|
| `openfda_client.py` | HTTP client for FDA's public API. Handles 403/network errors by auto-loading fallback. Reads `OPENFDA_API_KEY` at call time from `.env`. |
| `ctd_checklist.py` | Static data: 5 modules, 45 required ICH M4 sections as Python dicts. The ground truth for Mode 2. |
| `sample_faers.json` | 101 FAERS-format records for 7 drugs. Used as offline fallback when openFDA API is unavailable. |

### LLM Layer (`src/llm/`)
| File | Role |
|---|---|
| `client.py` | Wrapper around `ibm-watsonx-ai` SDK. Single function: `generate(prompt) → str`. Reads all credentials at call time. Returns stub if unconfigured. |
| `prompts.py` | Two prompt builders: one for signal rationale (Mode 1), one for gap report (Mode 2). Formats structured data into instructional prompts for Granite. |

### Frontend (`src/frontend/`)
| File | Role |
|---|---|
| `app.py` | Streamlit two-tab UI. Tab 1: drug name input → signal table. Tab 2: outline text area + file upload → readiness dashboard. Calls backend via `httpx`. |

### Configuration
| File | Role |
|---|---|
| `src/.env` | Your secrets (not committed). Read by every module at call time via `python-dotenv`. |
| `src/.env.example` | Template showing all required variable names. |
| `src/requirements.txt` | Python dependencies. Install with `pip install -r src/requirements.txt`. |

---

## 6. Environment Variables

| Variable | Used By | Required | What Happens If Missing |
|---|---|---|---|
| `WATSONX_API_KEY` | `llm/client.py` | For AI output | Returns stub text `[watsonx.ai not configured...]` |
| `WATSONX_PROJECT_ID` | `llm/client.py` | For AI output | Returns stub text |
| `WATSONX_URL` | `llm/client.py` | For AI output | Defaults to US South region |
| `WATSONX_MODEL_ID` | `llm/client.py` | No | Defaults to `ibm/granite-13b-instruct-v2` |
| `OPENFDA_API_KEY` | `data/openfda_client.py` | For >100 reports | Falls back to local 101-record sample dataset |
| `OPENFDA_BASE_URL` | `data/openfda_client.py` | No | Defaults to `https://api.fda.gov/drug/event.json` |
| `APP_PORT` | `run.py` | No | Defaults to `8000` |

All variables are loaded from `src/.env` using `python-dotenv` with `override=True`.

---

## 7. Ports

| Service | Port | URL |
|---|---|---|
| FastAPI backend | 8000 | http://localhost:8000 |
| Swagger API docs | 8000 | http://localhost:8000/docs |
| Streamlit frontend | 8501 | http://localhost:8501 |

To change the backend port: set `APP_PORT=8001` in `src/.env` and add `--port 8001` to the uvicorn command (or let `run.py` read it automatically).

---

## 8. What Happens With No Internet

The app is designed to work fully offline for demos:

1. **openFDA API unreachable** → `openfda_client.py` catches the error and loads `src/data/sample_faers.json` automatically. The UI shows a blue banner: *"Using offline fallback dataset"*. PRR computation runs on the 101-record sample.

2. **IBM watsonx.ai unreachable or unconfigured** → `llm/client.py` returns `[watsonx.ai not configured — set WATSONX_API_KEY...]`. The signal table and gap report still render; they just show the stub text instead of AI prose.

3. **Both APIs down** → The app still shows signal detection results from the fallback dataset and CTD completeness scores from the hardcoded checklist. All non-LLM functionality works completely offline.
