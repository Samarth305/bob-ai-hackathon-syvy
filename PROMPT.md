# Development Prompt — Drug Safety Signal Detector & Submission Readiness Checker (P2)

> Paste this whole file into IBM Bob (or whatever coding agent/LLM you're using) as your
> starting instruction. It's written so the agent can scaffold the entire repo in one pass.

---

## 1. Role & Context

You are an expert full-stack + applied-AI engineer helping a student team build an MVP for
the **IBM Bob AI Innovation Hackathon (CHARUSAT)**. First-round submission deadline is
**15 September, 12:00 PM–11:45 PM**. We have limited build time, so prioritize a working
end-to-end demo over polish. Favor simplicity, speed to a runnable demo, and honest
`known_limitations` over half-built ambitious features.

## 2. The Problem We're Solving (P2 — Pharma & Biotech, "Critical Now")

**Drug Safety Signal Detector & Regulatory Submission Readiness Checker**

FDA's FAERS database has 20M+ adverse event reports — too much for manual review, and
delayed signal detection has caused real harm (e.g. Vioxx). Separately, drug approval CTD
dossiers span 100,000+ pages across 5 modules; one missing section causes rejection, costing
6–12 months and $50–100M. Both problems share the same root cause: too much complex data
for manual review.

**Build two modes:**

1. **Signal Detection** — cluster adverse event reports and calculate PRR-style statistics
   to flag emerging safety signals.
2. **Submission Readiness** — check a dossier outline against ICH M4 CTD requirements,
   score completeness per module, and generate a gap report.

## 3. Required Repository Structure — DO NOT DEVIATE

We're using the official Bobathon submission template. These top-level files/folders
**already exist and must not be renamed, deleted, or restructured**:

```
├── submission.yaml          ← fill in completely, valid YAML, no empty required fields
├── README.md                ← replace every [placeholder] — no square brackets left anywhere
├── src/                     ← ALL source code goes here (subfolders are up to you)
│   ├── .env.example         ← list every env var the code actually uses
│   └── README.md
├── docs/
│   ├── problem-statement.md ← go deeper than README: audience, why existing tools fail,
│   │                          quantified pain, why it matters now
│   ├── solution-overview.md ← core mechanism, key design decisions, UX walkthrough
│   ├── architecture.md      ← MUST include a Mermaid diagram + component table
│   └── setup-guide.md       ← exact prereqs, env vars, install + run commands, a
│                              troubleshooting table — must work on a clean machine
├── demo/
│   ├── demo-video-link.txt  ← real URL (YouTube unlisted / Loom / Box), not the placeholder
│   ├── live-demo-url.txt    ← real URL or literally "NOT DEPLOYED"
│   └── screenshots/         ← at least 3, named 01-..., 02-..., 03-...
├── presentation/            ← slides.pdf or slides.pptx
├── CONTRIBUTING.md          ← do not delete
└── .github/workflows/validate.yml  ← do not modify
```

An automated GitHub Action validates on every push and will **fail the build (red ❌)** if:
- Any required file above is missing
- `submission.yaml` has invalid YAML or empty required fields (`team.name`, `team.track`,
  `team.lead.name`, `team.lead.email`, `submission.title`, `submission.problem_statement`,
  `submission.solution_summary`, at least 1 `key_features` entry)
- `team.track` isn't one of `AI | DevOps | Sustainability | Open` (use `AI`)
- `src/` has no files other than `README.md` / `.env.example`
- `demo/demo-video-link.txt` still contains the placeholder text
- `README.md` still contains `[Your Project Title Here]` or `[Your Team Name]`

Treat these as hard acceptance criteria — check them before considering any task "done."

## 4. Tech Stack (optimized for speed, not scale)

- **Backend**: Python + FastAPI — fast to write, easy to demo via `/docs` Swagger UI if the
  frontend runs short on time.
- **Frontend**: Streamlit — fastest path to a usable, demoable UI for two modes/tabs.
- **AI layer**: IBM watsonx.ai (Granite model) as the primary LLM for reasoning/summarization
  tasks (clustering rationale, gap-report language generation). **This is the "IBM Bob
  integration must be load-bearing" requirement — watsonx.ai should actually be called for
  a real reasoning step, not just referenced in docs.** Structure the LLM call behind a thin
  wrapper (`src/llm/client.py`) so it's swappable if watsonx access is delayed.
- **Data**: real data via the public openFDA FAERS API (`https://api.fda.gov/drug/event.json`,
  no key needed for low volume) for Mode 1. For Mode 2, hardcode the ICH M4 CTD module/
  section checklist as structured data (it's a fixed, publicly documented standard) and
  accept a user-uploaded or pasted dossier outline to check against it.
- **No database needed** — in-memory / JSON files are fine for an MVP demo.

## 5. Functional Spec

### Mode 1 — Signal Detection
1. Ingest a batch of FAERS adverse event reports (pull live via openFDA API, filtered by
   drug name the user enters; cache a local sample JSON as fallback if the API is
   unreachable during the demo).
2. Group reports by drug–adverse-event pair.
3. Compute a PRR (Proportional Reporting Ratio) for each pair:
   `PRR = (a/(a+b)) / (c/(c+d))` where a = reports of this event for this drug,
   b = reports of other events for this drug, c = reports of this event for other drugs,
   d = reports of other events for other drugs. Flag pairs with PRR ≥ 2 and a ≥ 3 as
   signals (standard pharmacovigilance threshold).
4. Pass the top flagged signals to the LLM to generate a plain-language rationale/summary
   per signal (this is your watsonx.ai integration point).
5. Display: ranked table of signals (drug, event, PRR, report count, LLM rationale).

### Mode 2 — Submission Readiness
1. Define the ICH M4 CTD structure as data: 5 modules (Administrative, Quality, Nonclinical,
   Clinical Overview, Clinical Study Reports — use the real module names), each with
   required sections.
2. Accept a dossier outline (paste text or upload a simple text/YAML list of sections
   present).
3. Diff the submitted outline against the required checklist per module.
4. Score completeness % per module and overall.
5. Use the LLM to generate a short gap report in judge-readable prose: what's missing, why
   it matters, suggested next step.

## 6. What to Build First (priority order for limited time)

1. `src/` skeleton + FastAPI backend with two endpoints (`/signals`, `/readiness`)
2. Mode 1 end-to-end with real openFDA data (this is your most demo-able, data-backed
   feature — get this rock solid first)
3. Streamlit frontend wired to both endpoints
4. Mode 2 with the hardcoded CTD checklist
5. LLM integration wrapper + wire into both modes
6. Fill every doc file, `submission.yaml`, `README.md`, take screenshots, record demo video
7. Push and confirm the GitHub Action is green

## 7. Non-Functional Requirements

- `.env.example` in `src/` must list every real env var used (e.g. `WATSONX_API_KEY`,
  `WATSONX_PROJECT_ID`, `WATSONX_URL`, `OPENFDA_API_KEY` if used, `APP_PORT`).
- Never commit `.env`, `node_modules/`, `.venv/`, `__pycache__/`, or build artifacts.
- Handle the "no internet / API down during judging" case gracefully — bundle a small
  cached sample dataset as fallback so the demo never shows a blank error screen.
- Write `known_limitations` in `submission.yaml` and the README honestly — e.g. "PRR
  thresholds are simplified pharmacovigilance heuristics, not clinically validated" or
  "CTD checklist covers section titles, not full regulatory depth." Judges respect honesty
  more than overclaiming, and it directly affects scoring.

## 8. Definition of Done

- [ ] Both modes run end-to-end locally following your own `setup-guide.md`, tested on a
      clean terminal
- [ ] watsonx.ai (or chosen LLM) call is real and demonstrably affects output, not
      decorative
- [ ] `submission.yaml` fully filled, valid YAML
- [ ] No `[placeholder]` text anywhere in `README.md`
- [ ] `docs/architecture.md` has a real Mermaid diagram reflecting the actual system
- [ ] 3+ screenshots in `demo/screenshots/`, real demo video link, live-demo-url.txt set
- [ ] `presentation/slides.pdf` present, covering: problem → solution → demo/architecture →
      IBM Bob/watsonx integration → impact
- [ ] Repo is Public, GitHub Actions "Validate Submission" is green
