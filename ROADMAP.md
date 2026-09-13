# ROADMAP.md — Build Plan for IBM Bob (or coding agent) to Execute

> Instruction to the agent: work through phases in order. Do not skip ahead to docs/demo
> polish while a phase's checkpoint is unmet. After each phase, run its checkpoint and
> report pass/fail before continuing. If a checkpoint fails, fix it before moving on —
> do not accumulate technical debt across phases; there is no time to backtrack later.

Context: see `PROMPT.md` for full functional spec (Drug Safety Signal Detector, P2).
This file sequences the work. Team has real build time only:
- **Today (Sun Sep 13)** — full day, this is the primary build window
- **Mon Sep 14** — only before 8:30am and after 9pm (office + gym all day)
- **Tue Sep 15** — only before 8:30am and after 9pm; submission form is only open
  12:00 PM–11:45 PM, so the actual submit action happens 9:00–11:45pm

Everything functional must be done by end of today. Mon/Tue are for docs, demo capture,
and the final push only — build no new features after today.

---

## Phase 0 — Repo Scaffold (target: first 30 min)

1. Create repo from the template (`Use this template`, not fork), name
   `bob-ai-hackathon-[team-name]`, set Public.
2. Clone locally.
3. Confirm the untouched top-level structure matches the template exactly — do not rename
   or delete `submission.yaml`, `CONTRIBUTING.md`, `.github/workflows/validate.yml`, or any
   `docs/`/`demo/` filenames.
4. Create the `src/` internal layout:
   ```
   src/
     backend/        # FastAPI app
     frontend/        # Streamlit app
     llm/             # watsonx.ai client wrapper
     data/            # openFDA client + CTD checklist data + cached fallback sample
     README.md        # update: describe this layout
     .env.example     # update: real vars used
     requirements.txt
   ```

**Checkpoint 0**: `git status` clean, repo pushed once, Actions tab shows a run (will be
red — that's expected, nothing is filled in yet).

---

## Phase 1 — Data Layer (target: next 1–1.5 hrs)

1. `src/data/openfda_client.py` — function to query
   `https://api.fda.gov/drug/event.json` filtered by drug name, returns raw reports.
2. `src/data/sample_faers.json` — a small cached sample (pull once, save to disk) as a
   fallback if the live API is unreachable during the demo.
3. `src/data/ctd_checklist.py` — hardcoded ICH M4 CTD structure: 5 modules, required
   sections per module, as a Python dict/list.
4. Write a throwaway script or test to confirm both data sources load correctly.

**Checkpoint 1**: Running the data layer standalone prints real FAERS records for at least
one drug name, and prints the full CTD checklist structure.

---

## Phase 2 — Backend Logic (target: next 2 hrs)

1. `src/backend/prr.py` — PRR calculation function per drug–event pair (see PROMPT.md §5
   for the formula and thresholds: PRR ≥ 2, a ≥ 3).
2. `src/backend/readiness.py` — diff a submitted dossier outline against the CTD checklist,
   compute completeness % per module and overall.
3. `src/backend/main.py` — FastAPI app with:
   - `POST /signals` — takes a drug name, returns ranked flagged signals
   - `POST /readiness` — takes a dossier outline, returns per-module scores + gaps
4. Test both endpoints locally via FastAPI's `/docs` Swagger UI with real inputs.

**Checkpoint 2**: Both endpoints return correct, non-empty, sensible JSON for a real test
input, callable via `/docs` — this is a demoable milestone even with no frontend yet.

---

## Phase 3 — LLM Integration (target: next 1 hr)

1. `src/llm/client.py` — thin wrapper around watsonx.ai (Granite model). Single function:
   takes a prompt, returns text. Keep it swappable (env-var-driven model choice) in case
   watsonx credentials aren't ready yet.
2. Wire into `/signals`: generate a plain-language rationale per flagged signal.
3. Wire into `/readiness`: generate a short judge-readable gap report from the scored diff.
4. **This is the IBM Bob/watsonx scoring criterion (10 pts) — verify the LLM call visibly
   changes the output**, not just decorative text.

**Checkpoint 3**: Calling `/signals` and `/readiness` now returns LLM-generated prose
alongside the numeric results. If watsonx access isn't working yet, stub with a clear
`TODO(watsonx)` and keep building — do not block downstream phases on this.

---

## Phase 4 — Frontend (target: next 1.5 hrs)

1. `src/frontend/app.py` — Streamlit app with two tabs: "Signal Detection" and "Submission
   Readiness", each calling the corresponding backend endpoint and rendering results in a
   table + the LLM prose.
2. Add basic input validation and a loading state (openFDA calls can be slow).
3. Handle the "API down" case by falling back to `sample_faers.json` without crashing.

**Checkpoint 4**: Full user journey works end-to-end through the UI: enter a drug name →
see ranked signals with rationale; paste a dossier outline → see completeness scores and
gap report.

---

## Phase 5 — Documentation (target: remaining time today + Mon early/late)

Fill in order of judge importance:
1. `docs/setup-guide.md` — write it, then actually test it on a clean terminal/teammate's
   machine. This is the single most commonly botched file.
2. `docs/architecture.md` — real Mermaid diagram of the actual system (frontend → FastAPI →
   watsonx.ai / openFDA), plus component table.
3. `docs/problem-statement.md` — depth per PROMPT.md §3.
4. `docs/solution-overview.md` — mechanism + design decisions + UX walkthrough.
5. `submission.yaml` — fill every required field, `team.track: "AI"`, list real
   `key_features`, honest `known_limitations`.
6. `README.md` — replace every `[placeholder]`; search the file for `[` to confirm none
   remain.

**Checkpoint 5**: `grep -r "\[Your" README.md` returns nothing; `submission.yaml` has no
empty required fields.

---

## Phase 6 — Demo Artifacts (target: Mon night / Tue early morning)

1. Take 3+ screenshots of the running app: `01-signal-detection.png`,
   `02-readiness-check.png`, `03-results-detail.png` (or similar), into `demo/screenshots/`.
2. Record a 3–5 min demo video: app starting up, a real signal-detection run, a real
   readiness-check run. Upload unlisted to YouTube/Loom/Box, put the real URL in
   `demo/demo-video-link.txt`.
3. `demo/live-demo-url.txt` — real URL if deployed, else literally `NOT DEPLOYED`.
4. Build `presentation/slides.pdf`: problem → solution → demo/architecture → Bob/watsonx
   integration → impact (5 slides is enough).

**Checkpoint 6**: Opening the video link and each screenshot in a fresh browser tab works
with no login/permission wall.

---

## Phase 7 — Final Validation & Submit (Tue, 9:00–11:45pm window)

1. `git add . && git commit -m "feat: complete submission" && git push`
2. Go to repo → Actions tab → confirm **✅ Validate Submission** is green. If red, open the
   run, read the specific failing check, fix it, push again — do not guess.
3. Confirm repo visibility is Public.
4. Confirm no `.env`, `node_modules/`, `.venv/`, or `__pycache__/` committed
   (`git log --all --full-history -- .env` should be empty).
5. Submit the repo URL via the CHARUSAT form before 11:45pm.

**Checkpoint 7 (final)**: Green Action + Public repo + form submitted. Do not leave this
until the last 15 minutes of the window.
