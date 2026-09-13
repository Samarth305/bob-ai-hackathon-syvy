# Build Plan — Drug Safety Signal Detector & Submission Readiness Checker

## Overview

**Goal**: Build the complete application from scratch. All documentation and metadata is done. The entire `src/` directory (backend, frontend, data layer, LLM wrapper) needs to be implemented, followed by demo artifacts and final validation.

**Scope**: Phases 1–7 of ROADMAP.md. Phase 5 (docs) and Phase 0 (scaffold) are already complete.

**Approach**: Build strictly in phase order per ROADMAP.md. Each subtask maps to a ROADMAP phase. Do not start a new phase until the previous checkpoint passes.

**Sources of truth**:
- `PROMPT.md` — full functional spec (PRR formula, ICH M4 modules, watsonx.ai requirement)
- `ROADMAP.md` — build sequence, checkpoints, time targets
- `docs/architecture.md` — component table, data flows, API schemas, directory structure
- `docs/solution-overview.md` — step-by-step flows, design decisions, ICH M4 checklist table
- `docs/setup-guide.md` — env vars, run commands, troubleshooting

---

## Subtask 0 — Fix src/ scaffold files

**Status**: [x] done

**Intent**: The `src/.env.example` contains wrong variables (DATABASE_URL, SLACK_WEBHOOK_URL) and `src/README.md` is still the generic template. Fix both before writing real code so all subsequent files are consistent with them.

**Expected Outcomes**:
- `src/.env.example` contains exactly: WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, WATSONX_MODEL_ID, APP_PORT, OPENFDA_BASE_URL — nothing else
- `src/README.md` describes the actual project layout matching ROADMAP.md Phase 0 spec

**Todo List**:
- [ ] Rewrite `src/.env.example` — remove DATABASE_URL, SLACK_WEBHOOK_URL; add WATSONX_MODEL_ID and OPENFDA_BASE_URL with correct defaults
- [ ] Rewrite `src/README.md` — describe backend/, frontend/, llm/, data/ layout; list key files

**Relevant Context**:
- `docs/setup-guide.md` — env vars table (lines 30–36 of current file)
- ROADMAP.md Phase 0 — `src/` internal layout spec
- PROMPT.md §7 — lists required env vars: WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, OPENFDA_API_KEY, APP_PORT

---

## Subtask 1 — Data Layer (ROADMAP Phase 1)

**Status**: [ ] pending

**Intent**: Build the two data sources the backend depends on — the live openFDA FAERS API client with offline fallback, and the hardcoded ICH M4 CTD checklist. These are pure data-access modules with no business logic.

**Expected Outcomes**:
- Running `python src/data/openfda_client.py` prints real FAERS records for at least one drug
- Running `python src/data/ctd_checklist.py` prints the full 5-module CTD structure
- `src/data/sample_faers.json` exists and contains valid FAERS-shaped records covering multiple drugs
- ROADMAP Checkpoint 1 passes

**Todo List**:
- [ ] Create `src/data/__init__.py`
- [ ] Create `src/data/openfda_client.py`:
  - Function `fetch_faers_reports(drug_name: str, limit: int = 1000) -> list[dict]`
  - Queries `https://api.fda.gov/drug/event.json?search=patient.drug.medicinalproduct:"DRUG"&limit=N`
  - On network error or non-200 response, automatically loads and returns `sample_faers.json`
  - Returns list of raw report dicts; includes a `fallback_used: bool` flag
- [ ] Create `src/data/sample_faers.json`:
  - Real FAERS-format records for at least 3 drugs: aspirin, ibuprofen, atorvastatin
  - ~200 records total (enough to compute meaningful PRR values)
  - Use real openFDA response structure: `results[].patient.drug[].medicinalproduct`, `results[].patient.reaction[].reactionmeddrapt`
- [ ] Create `src/data/ctd_checklist.py`:
  - Python dict `CTD_CHECKLIST` with 5 modules as keys
  - Each module: `name`, `description`, `sections` list
  - Sections derived from ICH M4 standard: Module 1 (6 sections), Module 2 (5 sections), Module 3 (12 sections), Module 4 (7 sections), Module 5 (8 sections)
  - Also export as `ctd_checklist.yaml` for human readability
- [ ] Create `src/requirements.txt` with all dependencies (needed for pip install in subsequent phases)

**Relevant Context**:
- PROMPT.md §5 Mode 1 step 1: "pull live via openFDA API, filtered by drug name"
- PROMPT.md §7: "Handle the 'no internet / API down during judging' case gracefully — bundle a small cached sample dataset as fallback"
- `docs/solution-overview.md` — ICH M4 CTD module table with 5 modules and required sections
- openFDA API endpoint: `https://api.fda.gov/drug/event.json` — public, no key needed for ≤1000 requests

---

## Subtask 2 — Backend Logic (ROADMAP Phase 2)

**Status**: [ ] pending

**Intent**: Build the two core computation modules (PRR calculator and CTD diff/scorer) and wire them into a FastAPI app with two endpoints. This is the demoable backend milestone — callable via Swagger UI without any frontend.

**Expected Outcomes**:
- `POST /signals` returns ranked table of drug–event pairs with PRR ≥ 2 and count ≥ 3 for a real drug name
- `POST /readiness` returns per-module completeness scores and list of missing sections for a sample dossier outline
- Both endpoints callable via `http://localhost:8000/docs` Swagger UI
- ROADMAP Checkpoint 2 passes

**Todo List**:
- [ ] Create `src/backend/__init__.py`
- [ ] Create `src/backend/prr.py`:
  - Input: list of FAERS report dicts from openfda_client
  - Parse each report into (drug_name, adverse_event_term) pairs
  - Build aggregation: count per (drug, event) pair = `a`; total events per drug = `a+b`; total reports of event across all drugs = `a+c`; grand total = `a+b+c+d`
  - Compute PRR = `(a/(a+b)) / (c/(c+d))` per pair
  - Filter: PRR ≥ 2.0 AND a ≥ 3
  - Return sorted list of dicts: drug, adverse_event, prr (float, 2dp), report_count, a, b, c, d
- [ ] Create `src/backend/readiness.py`:
  - Input: list of section title strings (user's dossier outline)
  - Load CTD_CHECKLIST from ctd_checklist.py
  - Normalize both lists (lowercase, strip, remove common prefixes)
  - Fuzzy match each required section against user outline (thefuzz, token_sort_ratio ≥ 80)
  - Mark each section PRESENT or MISSING
  - Compute per-module score: present/required * 100
  - Compute overall score
  - Return: overall_score, per-module list with score + missing sections list
- [ ] Create `src/backend/main.py`:
  - FastAPI app with CORS middleware (allow localhost:8501)
  - `POST /signals` endpoint: accepts `{drug_name: str, limit: int = 1000}`, calls openfda_client → prr → returns signals list + fallback_used flag
  - `POST /readiness` endpoint: accepts `{outline: list[str]}`, calls readiness checker, returns module scores + overall + missing sections
  - Both endpoints include Pydantic request/response models (defined in `src/backend/models.py`)
  - Health check: `GET /health` returns `{"status": "ok"}`
- [ ] Create `src/backend/models.py`:
  - Pydantic models for all request/response schemas (see docs/architecture.md API Endpoints section for exact shapes)

**Relevant Context**:
- PROMPT.md §5 Mode 1 steps 2–3: PRR formula and threshold (PRR ≥ 2, a ≥ 3)
- `docs/architecture.md` — API Endpoints section with exact JSON request/response shapes
- `docs/solution-overview.md` Mode 2 steps 3–5: fuzzy matching, per-module scoring

---

## Subtask 3 — LLM Integration (ROADMAP Phase 3)

**Status**: [ ] pending

**Intent**: Build the thin watsonx.ai wrapper and wire it into both endpoints so the LLM output is real and visibly changes the response. This is the IBM scoring criterion — must be a real inference call, not decorative.

**Expected Outcomes**:
- `POST /signals` response now includes a `rationale` field per signal, containing LLM-generated prose
- `POST /readiness` response now includes a `gap_report` string containing LLM-generated regulatory prose
- Running `python -m src.llm.client --test` confirms watsonx.ai connectivity and prints a response
- ROADMAP Checkpoint 3 passes

**Todo List**:
- [ ] Create `src/llm/__init__.py`
- [ ] Create `src/llm/prompts.py`:
  - `build_signal_rationale_prompt(signals: list[dict]) -> str` — formats top signals into a prompt asking Granite for plain-language clinical rationale per signal
  - `build_gap_report_prompt(missing_by_module: dict) -> str` — formats missing sections by module into a prompt asking for regulatory gap report prose
  - Both prompts include: task description, context (FAERS/ICH M4), output format instruction, and the actual data
- [ ] Create `src/llm/client.py`:
  - Load credentials from environment: WATSONX_API_KEY, WATSONX_PROJECT_ID, WATSONX_URL, WATSONX_MODEL_ID (default: `ibm/granite-13b-instruct-v2`)
  - Single public function: `generate(prompt: str) -> str`
  - Uses `ibm_watsonx_ai.foundation_models.ModelInference` with `TextGenParameters`
  - If WATSONX_API_KEY is not set or blank, return a clear stub string: `"[watsonx.ai not configured — set WATSONX_API_KEY in .env]"` rather than crashing
  - `if __name__ == "__main__"` block: run a test prompt and print the response (supports `--test` flag from setup-guide.md)
- [ ] Wire LLM into `/signals` endpoint in `src/backend/main.py`:
  - After PRR computation, call `build_signal_rationale_prompt` on top-10 signals
  - Call `generate(prompt)` to get rationale
  - Parse rationale back per signal (structure: numbered list matching signal order) and attach to each signal dict
- [ ] Wire LLM into `/readiness` endpoint in `src/backend/main.py`:
  - After scoring, call `build_gap_report_prompt` with missing sections per module
  - Call `generate(prompt)` and attach full response as `gap_report` string in response

**Relevant Context**:
- PROMPT.md §4: "IBM watsonx.ai (Granite model) ... watsonx.ai should actually be called for a real reasoning step, not just referenced in docs. Structure the LLM call behind a thin wrapper (src/llm/client.py) so it's swappable"
- PROMPT.md §3: "team.track must be AI — IBM Bob/watsonx integration must be load-bearing (10 pts scoring criterion)"
- `docs/solution-overview.md` — IBM Technologies Used section describes exactly what the LLM should do in each mode

---

## Subtask 4 — Frontend (ROADMAP Phase 4)

**Status**: [ ] pending

**Intent**: Build the Streamlit two-tab UI that makes the application demoable end-to-end from a browser. Each tab calls the corresponding backend endpoint and renders results in a way a non-technical judge can understand.

**Expected Outcomes**:
- Opening `http://localhost:8501` shows a two-tab app
- Signal Detection tab: enter drug name, click button, see ranked table with PRR + rationale
- Submission Readiness tab: paste/upload outline, click button, see module scores dashboard + gap report
- Offline fallback notice shown when openFDA API unreachable
- ROADMAP Checkpoint 4 passes (full end-to-end user journey works)

**Todo List**:
- [ ] Create `src/frontend/__init__.py`
- [ ] Create `src/frontend/app.py`:
  - Two tabs: "🔬 Signal Detection" and "📋 Submission Readiness"
  - **Signal Detection tab**:
    - Text input: drug name
    - Number input: limit (default 1000, range 100–5000)
    - "Run Signal Analysis" button with loading spinner
    - On click: POST to `http://localhost:8000/signals`
    - If `fallback_used == true`, show info banner: "Using offline fallback dataset"
    - Results: st.dataframe with columns Drug, Adverse Event, PRR, Report Count
    - Below each row or in expander: LLM rationale text
    - Summary metrics: total reports, signals flagged, highest PRR
    - Empty state: "No signals found meeting threshold (PRR ≥ 2, count ≥ 3)"
  - **Submission Readiness tab**:
    - Text area: paste dossier outline (one section per line)
    - File uploader: .txt or .yaml file as alternative input
    - "Check Readiness" button with loading spinner
    - On click: POST to `http://localhost:8000/readiness`
    - Overall score: large colored metric (green ≥ 80%, yellow 50-79%, red < 50%)
    - Per-module progress bars (5 bars, one per CTD module) with present/required counts
    - Expandable missing sections list per module
    - LLM gap report displayed as formatted text
  - Backend URL configurable via `BACKEND_URL` env var (default: `http://localhost:8000`)
  - Error handling: if backend unreachable, show clear error message not a traceback

**Relevant Context**:
- `docs/solution-overview.md` — UX Walkthrough section describes exact expected behavior for both modes
- PROMPT.md §4: "Streamlit — fastest path to a usable, demoable UI for two modes/tabs"
- ROADMAP.md Phase 4: "Add basic input validation and a loading state (openFDA calls can be slow)"

---

## Subtask 5 — Demo Artifacts (ROADMAP Phase 6)

**Status**: [ ] pending

**Intent**: Capture the 3 required screenshots and create the missing demo support files. The demo video recording and presentation slides are manual tasks, but supporting text files and the demo outline can be created now.

**Expected Outcomes**:
- `demo/demo-video-link.txt` contains a real URL (not placeholder) — **required for CI to pass**
- `demo/live-demo-url.txt` contains "NOT DEPLOYED" or a real URL — **required for CI to pass**
- `demo/demo-outline-example.txt` exists with a pre-built partial CTD outline for judges
- `demo/screenshots/` has placeholder README explaining what screenshots are needed
- `presentation/slides.pdf` or `presentation/slides.pptx` exists

**Todo List**:
- [ ] Create `demo/demo-outline-example.txt` — pre-built partial CTD outline for Mode 2 demo (covers ~60% of required sections to produce meaningful gap report)
- [ ] Update `demo/live-demo-url.txt` — replace placeholder with "NOT DEPLOYED — run locally using docs/setup-guide.md"
- [ ] Screenshots: after app is running, capture `demo/screenshots/01-signal-detection.png`, `02-readiness-checker.png`, `03-gap-report.png`
- [ ] Video: record 3–5 min demo of both modes, upload to YouTube unlisted or Loom, update `demo/demo-video-link.txt`
- [ ] Slides: build `presentation/slides.pdf` covering: problem → solution → architecture/demo → watsonx.ai integration → impact

**Relevant Context**:
- ROADMAP.md Phase 6: screenshot naming conventions, video requirements
- PROMPT.md §3 validation rules: "demo/demo-video-link.txt still contains the placeholder text" → CI fails

---

## Subtask 6 — Final Validation (ROADMAP Phase 7)

**Status**: [ ] pending

**Intent**: Verify GitHub Actions passes, repo is public, no secrets committed, submission form filled.

**Expected Outcomes**:
- GitHub Actions "Validate Submission" shows ✅ green
- `git log --all --full-history -- .env` returns empty
- Repo visibility is Public
- Submission form submitted before 11:45pm Tue Sep 15

**Todo List**:
- [ ] Push all changes: `git add . && git commit -m "feat: complete submission" && git push`
- [ ] Verify Actions tab shows green run
- [ ] If red: read specific failing check, fix, push again
- [ ] Confirm no .env, .venv/, __pycache__/ committed
- [ ] Confirm repo is Public
- [ ] Submit repo URL via CHARUSAT form before 11:45pm Tue Sep 15

**Relevant Context**:
- ROADMAP.md Phase 7 — exact git verification commands
- PROMPT.md §3 validation rules — full list of CI failure conditions

---

## Implementation Notes

- Start each subtask by reading this plan file for full context
- After each subtask, update the status in this file from `[ ] pending` to `[x] done`
- Do not start Subtask 2 until Subtask 1 checkpoint passes (running data layer prints real FAERS records)
- Do not start Subtask 4 until Subtask 3 is wired (LLM must be in both endpoints before frontend)
- The `--test` flag for `src/llm/client.py` is referenced in `docs/setup-guide.md` — implement it exactly
- The `demo/demo-outline-example.txt` is referenced in `docs/setup-guide.md` Demo Walkthrough section — create it
