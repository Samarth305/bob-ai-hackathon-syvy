# QUICKSTART — How to Run, Check, and Test

> One-stop reference for running the app locally, verifying each component works,
> and running the test suite. Keep this open in a browser tab during development.

---

## 0. One-time Setup

> **Run these steps once** on a fresh machine. After that, just use `python run.py`.

All commands below are run from the **repo root** — the folder that contains `run.py`,
`README.md`, `src/`, etc. **Not** from inside `src/`.

---

### Step 0-A — Open a terminal in the repo root

| OS | How to open terminal here |
|---|---|
| **Windows** | Open File Explorer → navigate to the repo folder → click address bar → type `powershell` → Enter |
| **macOS** | Right-click the folder in Finder → "New Terminal at Folder" (or `cd` to it in Terminal) |
| **Linux** | `cd ~/path/to/bob-ai-hackathon-syvy` |

Confirm you are in the right place:
```
# You should see run.py listed:
ls          # macOS / Linux
dir         # Windows PowerShell
```

---

### Step 0-B — Create the virtual environment

Run this **once** from the repo root:

```bash
# macOS / Linux
python3 -m venv .venv

# Windows PowerShell
python -m venv .venv
```

This creates a `.venv/` folder inside the repo. It only needs to be created once.

---

### Step 0-C — Activate the virtual environment

You must activate the venv **every time you open a new terminal**.
After activation you will see `(.venv)` at the start of your prompt.

```bash
# macOS / Linux — run this in your terminal:
source .venv/bin/activate

# Windows PowerShell — run this:
.venv\Scripts\Activate.ps1

# Windows Command Prompt (cmd.exe) — run this:
.venv\Scripts\activate.bat
```

**How to tell it worked:**
```
# Before activation:
C:\Users\you\bob-ai-hackathon-syvy>

# After activation — (.venv) appears:
(.venv) C:\Users\you\bob-ai-hackathon-syvy>
```

> **Windows note:** If you see `running scripts is disabled`, run this once in PowerShell as Administrator:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

---

### Step 0-D — Install dependencies

With the venv **activated**, run from the repo root:

```bash
pip install -r src/requirements.txt
```

This installs FastAPI, Streamlit, watsonx.ai SDK, pandas, and all other dependencies
into your `.venv`. Takes 1–3 minutes. Only needs to be done once (or again if
`src/requirements.txt` changes).

**Verify it worked:**
```bash
uvicorn --version    # should print: Running uvicorn x.x.x with CPython ...
streamlit --version  # should print: Streamlit, version x.x.x
```

---

### Step 0-E — Set up environment variables

```bash
# macOS / Linux
cp src/.env.example src/.env

# Windows PowerShell
Copy-Item src\.env.example src\.env
```

Then open `src/.env` in any text editor (Notepad, VS Code, etc.) and fill in:

```
WATSONX_API_KEY=<your IBM Cloud API key>
WATSONX_PROJECT_ID=<your watsonx.ai project ID>
WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

> See `src/.env.example` for instructions on where to get each value.
> The app works without these (LLM fields will show a stub notice), but
> the IBM watsonx.ai AI output will not work until they are set.

---

## 1. Start the Application

> The `run.py` script **automatically detects and uses your `.venv`** — you do not
> need to manually activate it every time before running. Just run the command from
> the repo root.

### One command (recommended)

**macOS / Linux:**
```bash
# From the repo root:
python3 run.py
```

**Windows PowerShell:**
```powershell
# From the repo root:
python run.py
```

**Windows — double-click shortcut:**
Double-click `run.bat` in File Explorer. A terminal window opens and both servers start.

**macOS / Linux — shell shortcut:**
```bash
# Make executable once:
chmod +x run.sh

# Then just run:
./run.sh
```

That's it. Both the backend and frontend start together, the browser opens automatically
at **http://localhost:8501**, and a single `Ctrl+C` stops everything cleanly.

**OS shortcuts:**
```bash
# macOS / Linux (make executable once: chmod +x run.sh)
./run.sh

# Windows — double-click run.bat, or in PowerShell:
.\run.bat
```

**Expected output:**
```
============================================================
  Drug Safety Signal Detector & Submission Readiness Checker
============================================================

Starting backend  (FastAPI)...
  Waiting for backend on :8000... ready
Starting frontend (Streamlit)...
  Waiting for frontend on :8501... ready

============================================================
  ✅  App is running!

  🌐  UI       →  http://localhost:8501
  📡  API      →  http://localhost:8000
  📖  Swagger  →  http://localhost:8000/docs

  Press  Ctrl+C  to stop both servers
============================================================
```

### Other run.py options

```bash
python run.py --no-browser   # start without auto-opening the browser
python run.py --check        # pre-flight environment check only (does not start)
python run.py --stop         # kill any already-running instances on ports 8000/8501
```

### Manual two-terminal start (fallback)

If `run.py` doesn't work for any reason, start each process manually:

```bash
# Terminal 1 — backend
cd src && uvicorn backend.main:app --reload --port 8000

# Terminal 2 — frontend
cd src && streamlit run frontend/app.py
```

---

## 2. Verify Each Component Works

### 2a. Data Layer — openFDA Client

```bash
cd src
python data/openfda_client.py
```

**Expected output (live API):**
```
Fetching FAERS reports for drug: aspirin (limit=10)
Fetched 10 reports from openFDA API. fallback_used=False
Sample report keys: ['safetyreportid', 'patient', 'receivedate', ...]
Drug terms found: ['ASPIRIN', 'ASPIRIN 81MG', ...]
Adverse events found: ['CHEST PAIN', 'DYSPNOEA', 'NAUSEA', ...]
✅ openFDA client OK
```

**Expected output (no internet / fallback):**
```
openFDA API unreachable — loading local fallback sample.
Loaded 200 reports from sample_faers.json. fallback_used=True
✅ Fallback dataset OK
```

---

### 2b. Data Layer — CTD Checklist

```bash
cd src
python data/ctd_checklist.py
```

**Expected output:**
```
ICH M4 CTD Checklist — 5 modules loaded:
  Module 1: Administrative Information      —  6 required sections
  Module 2: CTD Summaries & Overviews       —  5 required sections
  Module 3: Quality                         — 12 required sections
  Module 4: Nonclinical Study Reports       —  7 required sections
  Module 5: Clinical Study Reports          —  8 required sections
Total required sections: 38
✅ CTD checklist OK
```

---

### 2c. Backend — PRR Calculation (unit check)

```bash
cd src
python backend/prr.py
```

**Expected output:**
```
Running PRR self-test with sample_faers.json...
Loaded 200 FAERS reports
Drug-event pairs extracted: N
Signals flagged (PRR >= 2.0, count >= 3): N
Top 3 signals:
  1. ASPIRIN | Gastrointestinal haemorrhage | PRR=X.XX | count=N
  2. ...
✅ PRR calculator OK
```

---

### 2d. Backend — Readiness Checker (unit check)

```bash
cd src
python backend/readiness.py
```

**Expected output:**
```
Running readiness self-test with sample outline...
Submitted 7 sections; Required 38 sections
Overall score: 18.4%
Module scores:
  Module 1 — Administrative:   3/6 = 50.0%
  Module 2 — Summaries:        2/5 = 40.0%
  Module 3 — Quality:          1/12 =  8.3%
  Module 4 — Nonclinical:      0/7 =  0.0%
  Module 5 — Clinical:         1/8 = 12.5%
Missing sections (sample): ['1.2 Application form', '1.4 Information about the experts', ...]
✅ Readiness checker OK
```

---

### 2e. LLM — watsonx.ai Connectivity

```bash
cd src
python -m llm.client --test
```

**Expected output (credentials configured):**
```
watsonx.ai connectivity test
  URL:     https://us-south.ml.cloud.ibm.com
  Project: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
  Model:   ibm/granite-13b-instruct-v2
Sending test prompt...
Response received (N tokens):
  "Pharmacovigilance is the science of detecting, assessing..."
✅ watsonx.ai LLM OK
```

**Expected output (no credentials / WATSONX_API_KEY not set):**
```
⚠️  WATSONX_API_KEY not set — LLM will return stub responses.
    Set WATSONX_API_KEY in src/.env to enable real AI output.
```
> This is non-fatal. The app still runs — signal rationale and gap report fields will contain a stub notice instead of real LLM text.

---

### 2f. Backend API — Full Endpoint Test via curl

**Signal Detection:**
```bash
curl -X POST http://localhost:8000/signals \
  -H "Content-Type: application/json" \
  -d '{"drug_name": "aspirin", "limit": 100}'
```

**Expected response shape:**
```json
{
  "drug_name": "aspirin",
  "total_reports": 100,
  "fallback_used": false,
  "signals": [
    {
      "drug": "aspirin",
      "adverse_event": "Gastrointestinal haemorrhage",
      "prr": 4.73,
      "report_count": 12,
      "rationale": "Aspirin inhibits COX-1, reducing prostaglandin-mediated..."
    }
  ]
}
```

**Submission Readiness:**
```bash
curl -X POST http://localhost:8000/readiness \
  -H "Content-Type: application/json" \
  -d '{
    "outline": [
      "1.0 Cover letter",
      "2.3 Quality Overall Summary",
      "2.5 Clinical Overview",
      "3.2.S Drug Substance",
      "5.5 Clinical Efficacy Studies"
    ]
  }'
```

**Expected response shape:**
```json
{
  "overall_score": 13.2,
  "modules": [
    {
      "module": "Module 1 — Administrative Information",
      "score": 16.7,
      "present": 1,
      "required": 6,
      "missing": ["1.2 Application form", "1.3 Prescribing information", "..."]
    }
  ],
  "gap_report": "The submitted dossier outline is missing critical sections..."
}
```

---

### 2g. Swagger UI (browser-based test)

Open: **http://localhost:8000/docs**

1. Click `POST /signals` → "Try it out"
2. Set body: `{"drug_name": "ibuprofen", "limit": 100}`
3. Click "Execute" → verify 200 response with signals list

4. Click `POST /readiness` → "Try it out"
5. Paste the demo outline from `demo/demo-outline-example.txt`
6. Click "Execute" → verify 200 response with module scores + gap_report

---

### 2h. Full UI Smoke Test

1. Open **http://localhost:8501**
2. **Signal Detection tab:**
   - Type: `atorvastatin`
   - Click "Run Signal Analysis"
   - ✅ Expect: ranked table with PRR column and LLM rationale text
3. **Submission Readiness tab:**
   - Open `demo/demo-outline-example.txt`, copy all contents
   - Paste into the text area
   - Click "Check Readiness"
   - ✅ Expect: five progress bars (module scores) + gap report paragraph

---

## 3. Run the Test Suite

```bash
cd src
pytest tests/ -v
```

**Expected output:**
```
tests/test_prr.py::test_prr_basic_signal PASSED
tests/test_prr.py::test_prr_no_signal_below_threshold PASSED
tests/test_prr.py::test_prr_minimum_count_filter PASSED
tests/test_prr.py::test_prr_formula_correctness PASSED
tests/test_readiness.py::test_perfect_score PASSED
tests/test_readiness.py::test_empty_outline PASSED
tests/test_readiness.py::test_partial_outline PASSED
tests/test_readiness.py::test_fuzzy_match_section_names PASSED
tests/test_openfda.py::test_fallback_on_network_error PASSED
tests/test_openfda.py::test_fallback_dataset_valid_structure PASSED

10 passed in X.XXs
```

**Run a single test file:**
```bash
pytest tests/test_prr.py -v
```

**Run with coverage:**
```bash
pytest tests/ --cov=backend --cov=data --cov-report=term-missing
```

---

## 4. Common Issues & Fixes

| Symptom | Cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'fastapi'` | venv not activated or deps not installed | `source .venv/bin/activate` then `pip install -r src/requirements.txt` |
| `ModuleNotFoundError: No module named 'backend'` | Running from wrong directory | Make sure you `cd src` before running uvicorn or pytest |
| `uvicorn: command not found` | venv not activated | `source .venv/bin/activate` |
| `curl: connection refused` (port 8000) | Backend not running | Start Terminal 1 with uvicorn command |
| Streamlit shows "Connection refused" | Backend not running | Start Terminal 1 with uvicorn command |
| `WATSONX_API_KEY not set` warning | `.env` missing or empty | `cp src/.env.example src/.env` then edit the file |
| `401 Unauthorized` from watsonx.ai | Wrong or expired API key | Regenerate key at IBM Cloud → IAM → API Keys |
| `404 Not Found` from watsonx.ai | Wrong WATSONX_URL region | Check IBM Cloud → Resource list → watsonx.ai endpoint URL |
| openFDA returns empty results | Drug name spelling | Try exact brand/generic name: `aspirin`, `ibuprofen`, `metformin` |
| PRR table empty | No signals above threshold | Normal for some drugs — try `atorvastatin` or use fallback with `aspirin` |
| `thefuzz` import error | python-Levenshtein missing | `pip install python-Levenshtein` (optional speedup, not required) |
| Port 8000 already in use | Another process running | `lsof -ti:8000 | xargs kill` (macOS/Linux) or use `--port 8001` |
| Port 8501 already in use | Another Streamlit running | `pkill -f streamlit` (macOS/Linux) or end via Task Manager (Windows) |

---

## 5. Environment Checklist Before Demo

Run this checklist right before recording or showing to judges:

```bash
# 1. Confirm venv is active (you should see (.venv) in prompt)
python --version            # should be 3.11+

# 2. Confirm backend starts clean
cd src && uvicorn backend.main:app --port 8000
# check: no errors in startup output

# 3. Confirm health endpoint
curl http://localhost:8000/health
# expected: {"status":"ok"}

# 4. Confirm watsonx.ai works
python -m llm.client --test
# expected: response received, not stub

# 5. Confirm openFDA works (or fallback is ready)
python data/openfda_client.py
# expected: either live fetch or "fallback OK"

# 6. Run full test suite one more time
pytest tests/ -v
# expected: all green

# 7. Open http://localhost:8501 and do the smoke test (section 2h above)
```

---

## 6. File Locations Quick Reference

| What you need | Where it is |
|---|---|
| Environment variable template | `src/.env.example` |
| All Python dependencies | `src/requirements.txt` |
| FastAPI app entry point | `src/backend/main.py` |
| Streamlit UI | `src/frontend/app.py` |
| PRR computation logic | `src/backend/prr.py` |
| CTD checklist diff logic | `src/backend/readiness.py` |
| watsonx.ai wrapper | `src/llm/client.py` |
| openFDA fetcher | `src/data/openfda_client.py` |
| Offline fallback data | `src/data/sample_faers.json` |
| ICH M4 CTD checklist | `src/data/ctd_checklist.py` |
| Demo CTD outline for paste | `demo/demo-outline-example.txt` |
| All test files | `src/tests/` |
| Full setup instructions | `docs/setup-guide.md` |
| Architecture diagram | `docs/architecture.md` |
