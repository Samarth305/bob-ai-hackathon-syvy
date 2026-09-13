# Source Code — Drug Safety Signal Detector & Submission Readiness Checker

This directory contains all application source code. See [`docs/setup-guide.md`](../docs/setup-guide.md) for full install and run instructions.

---

## Directory Layout

```
src/
├── backend/                  # FastAPI REST API
│   ├── main.py               # App entry point; POST /signals, POST /readiness, GET /health
│   ├── models.py             # Pydantic request/response schemas
│   ├── prr.py                # PRR (Proportional Reporting Ratio) computation
│   ├── readiness.py          # CTD checklist diff + completeness scoring
│   └── __init__.py
│
├── frontend/                 # Streamlit web UI
│   ├── app.py                # Two-tab app: Signal Detection | Submission Readiness
│   └── __init__.py
│
├── llm/                      # IBM watsonx.ai integration
│   ├── client.py             # Granite model wrapper — single generate(prompt) function
│   ├── prompts.py            # Prompt builders for Mode 1 (signals) and Mode 2 (gap report)
│   └── __init__.py
│
├── data/                     # Data sources and static reference data
│   ├── openfda_client.py     # openFDA FAERS API fetcher + offline fallback loader
│   ├── ctd_checklist.py      # ICH M4 CTD 5-module checklist as Python dict
│   ├── sample_faers.json     # Bundled fallback dataset (~200 FAERS reports, 3 drugs)
│   ├── ctd_checklist.yaml    # Human-readable copy of the CTD checklist
│   └── __init__.py
│
├── tests/                    # Test suite
│   ├── test_prr.py           # Unit tests for PRR computation
│   ├── test_readiness.py     # Unit tests for CTD diff and scoring
│   ├── test_openfda.py       # Tests for FAERS fetcher (uses fallback)
│   └── __init__.py
│
├── .env.example              # Template — copy to .env and fill in values
├── requirements.txt          # Python dependencies
└── README.md                 # This file
```

---

## Quick Start

```bash
# From repo root — one-time setup
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r src/requirements.txt
cp src/.env.example src/.env       # then edit src/.env

# Terminal 1 — backend
cd src && uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd src && streamlit run frontend/app.py
```

Open **http://localhost:8501** for the UI, or **http://localhost:8000/docs** for Swagger.

---

## Key Files

| File | Purpose |
|---|---|
| `backend/main.py` | FastAPI app — start here to understand the API |
| `backend/prr.py` | Core PRR formula: `(a/(a+b)) / (c/(c+d))` |
| `backend/readiness.py` | CTD section diff and completeness % per module |
| `llm/client.py` | IBM watsonx.ai call — `generate(prompt) -> str` |
| `data/openfda_client.py` | openFDA FAERS query + local fallback |
| `data/ctd_checklist.py` | ICH M4 standard — 5 modules, required sections |
| `frontend/app.py` | Streamlit two-tab UI |

---

## Environment Variables

Copy `src/.env.example` to `src/.env` and fill in:

| Variable | Required | Default |
|---|---|---|
| `WATSONX_API_KEY` | Yes | — |
| `WATSONX_PROJECT_ID` | Yes | — |
| `WATSONX_URL` | Yes | `https://us-south.ml.cloud.ibm.com` |
| `WATSONX_MODEL_ID` | No | `ibm/granite-13b-instruct-v2` |
| `APP_PORT` | No | `8000` |
| `OPENFDA_BASE_URL` | No | `https://api.fda.gov/drug/event.json` |
| `OPENFDA_API_KEY` | No | — |

---

## What NOT to Commit

- `src/.env` — contains real secrets
- `src/.venv/` or `.venv/` — virtual environment
- `src/__pycache__/` or any `*.pyc` — build artifacts
- Large binary model files
