# Setup Guide

> **This file is read by the automated evaluation pipeline. Be precise and complete.**
> All commands below are tested on macOS/Linux and Windows (PowerShell). Run them in order on a clean machine.

---

## Prerequisites

Before you begin, ensure you have the following installed and configured:

- [ ] **Python 3.11 or higher** — `python --version` or `python3 --version`
- [ ] **pip** (bundled with Python 3.11+)
- [ ] **git** — `git --version`
- [ ] **An IBM Cloud account** with watsonx.ai access
  - Create at: https://cloud.ibm.com/registration
  - Provision a watsonx.ai project at: https://dataplatform.cloud.ibm.com
  - Note your **API key**, **Project ID**, and **service URL** (region-specific, e.g. `https://us-south.ml.cloud.ibm.com`)
- [ ] **Internet access** during setup (for pip install and openFDA API). The app works offline for demos using the bundled fallback dataset.

---

## Environment Variables

All secrets are loaded from a `.env` file. **Never commit `.env` to git.**

```bash
# From the repo root:
cp src/.env.example src/.env
```

Open `src/.env` in a text editor and fill in the values:

| Variable | Description | Required | Example |
|---|---|---|---|
| `WATSONX_API_KEY` | IBM Cloud API key (IAM) | **Yes** | `abc123xyz...` |
| `WATSONX_PROJECT_ID` | watsonx.ai project ID (UUID) | **Yes** | `f1234567-89ab-...` |
| `WATSONX_URL` | watsonx.ai service endpoint | **Yes** | `https://us-south.ml.cloud.ibm.com` |
| `WATSONX_MODEL_ID` | Granite model ID | No (has default) | `ibm/granite-13b-instruct-v2` |
| `APP_PORT` | FastAPI backend port | No (default: 8000) | `8000` |
| `OPENFDA_BASE_URL` | openFDA API base URL | No (has default) | `https://api.fda.gov/drug/event.json` |

### How to get your IBM watsonx.ai credentials

1. **API Key**: IBM Cloud → Manage → Access (IAM) → API Keys → Create → Copy key
2. **Project ID**: watsonx.ai dashboard → your project → Manage → General → Project ID
3. **Service URL**: Depends on region:
   - US South: `https://us-south.ml.cloud.ibm.com`
   - EU Germany: `https://eu-de.ml.cloud.ibm.com`
   - Tokyo: `https://jp-tok.ml.cloud.ibm.com`
   - London: `https://eu-gb.ml.cloud.ibm.com`

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/bob-ai-hackathon-syvy.git
cd bob-ai-hackathon-syvy
```

### 2. Create and Activate a Virtual Environment

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

You should see `(.venv)` in your terminal prompt after activation.

### 3. Install Dependencies

```bash
pip install -r src/requirements.txt
```

This installs:
- `fastapi` + `uvicorn[standard]` — backend server
- `streamlit` — frontend UI
- `httpx` — async HTTP client for openFDA API calls
- `pandas` — PRR computation
- `pyyaml` — CTD checklist loading
- `python-dotenv` — environment variable loading
- `ibm-watsonx-ai` — IBM watsonx.ai Python SDK
- `thefuzz` — fuzzy string matching for CTD section comparison
- `pydantic` — request/response schema validation

### 4. Configure Environment

```bash
cp src/.env.example src/.env
# Edit src/.env with your WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL
```

---

## Running the Application

You need **two terminals** — one for the backend, one for the frontend.

### Terminal 1 — Start the FastAPI Backend

```bash
# From the repo root, with .venv activated:
cd src
uvicorn api.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Started reloader process
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
```

The Swagger UI is available at: **http://localhost:8000/docs**

### Terminal 2 — Start the Streamlit Frontend

```bash
# Open a new terminal, activate .venv, then from the repo root:
cd src
streamlit run frontend/app.py
```

You should see:
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
  Network URL: http://192.168.x.x:8501
```

The application is now available at: **http://localhost:8501**

---

## Verifying the Installation

### Quick Smoke Test — Signal Detection

1. Open http://localhost:8501
2. On the **Signal Detection** tab, type `ibuprofen` in the drug name field
3. Click **Run Signal Analysis**
4. Expected: A ranked table of drug–event pairs with PRR values and LLM-generated rationale
5. If the openFDA API is unreachable, the app automatically uses the bundled fallback dataset (you will see a notice: "Using offline fallback dataset")

### Quick Smoke Test — Submission Readiness

1. Click the **Submission Readiness** tab
2. Paste the following minimal outline into the text area:
   ```
   1.0 Cover letter
   2.3 Quality Overall Summary
   2.5 Clinical Overview
   3.2.S Drug Substance — Nomenclature
   3.2.S Drug Substance — Structure
   4.2.1 Primary Pharmacology
   5.5 Efficacy and Safety Studies
   ```
3. Click **Check Readiness**
4. Expected: A completeness dashboard showing per-module scores, a list of missing sections, and an LLM-generated gap report

### Verify watsonx.ai Integration

Run the standalone LLM test:

```bash
cd src
python -m llm.client --test
```

Expected output:
```
watsonx.ai connection: OK
Model: ibm/granite-13b-instruct-v2
Test prompt response received (N tokens)
```

If you see a `401 Unauthorized` error, check your `WATSONX_API_KEY` in `src/.env`.

---

## Running Tests

```bash
cd src
pytest tests/ -v
```

---

## Troubleshooting

| Issue | Likely Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | Virtual environment not activated or deps not installed | Run `source .venv/bin/activate` then `pip install -r src/requirements.txt` |
| `ImportError: cannot import name 'ibm_watsonx_ai'` | Old version of SDK installed | Run `pip install --upgrade ibm-watsonx-ai` |
| `WATSONX_API_KEY not set` | `.env` file missing or not in `src/` directory | Confirm `src/.env` exists and contains `WATSONX_API_KEY=...` |
| `401 Unauthorized` from watsonx.ai | Invalid or expired API key | Regenerate API key in IBM Cloud IAM console |
| `404 Not Found` from watsonx.ai | Wrong `WATSONX_URL` for your region | Check region in IBM Cloud → Resource list → watsonx.ai instance → Endpoint URL |
| `openFDA API: ConnectionError` | No internet access | Expected behavior — app automatically switches to bundled fallback dataset |
| Streamlit shows `Connection refused` | FastAPI backend not running | Ensure `uvicorn api.main:app --reload --port 8000` is running in Terminal 1 |
| `Port 8000 already in use` | Another process on port 8000 | Either kill the other process, or set `APP_PORT=8001` in `.env` and use `--port 8001` in uvicorn command |
| `Port 8501 already in use` | Another Streamlit instance running | Kill existing Streamlit process: `pkill -f streamlit` (macOS/Linux) or end task in Task Manager (Windows) |
| PRR table is empty | Drug name not found in FAERS sample | Try a common drug name: `aspirin`, `ibuprofen`, `metformin`, `atorvastatin`. For the fallback dataset, use `aspirin`. |
| `thefuzz` fuzzy matching too strict | CTD section titles don't match checklist | The matcher uses 80% similarity threshold; try standard ICH M4 section naming (e.g., "3.2.S" prefix format) |

---

## Demo Walkthrough (Recommended for Judges)

For the fastest path to seeing the core value:

```bash
# Terminal 1 — backend
cd src && uvicorn api.main:app --reload --port 8000

# Terminal 2 — frontend
cd src && streamlit run frontend/app.py

# Open http://localhost:8501
# Signal Detection: search "atorvastatin" → see statin-related signals with LLM rationale
# Submission Readiness: use demo outline from demo/demo-outline-example.txt
```

The `demo/demo-outline-example.txt` file contains a pre-built partial CTD outline that demonstrates both present and missing sections to produce a meaningful readiness score and gap report.
