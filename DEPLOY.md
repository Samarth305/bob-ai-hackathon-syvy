# Deployment Guide — Render (free tier, shareable URL)

This project runs two services — a **FastAPI backend** and a **Streamlit frontend**.
The instructions below deploy both to [Render](https://render.com) and give you two public URLs,
one of which you can share.

---

## Files added for deployment

| File | Purpose |
|---|---|
| `Dockerfile.backend` | Containerises the FastAPI API on port 8000 |
| `Dockerfile.frontend` | Containerises the Streamlit UI on port 8501 |
| `docker-compose.yml` | Runs both services locally with one command |
| `render.yaml` | Render Blueprint — declares both services |

---

## Option A — Deploy to Render (recommended, free, shareable URL)

### Prerequisites
- A [Render account](https://dashboard.render.com/register) (free)
- This repo pushed to GitHub (public or private — Render supports both)
- Your `WATSONX_API_KEY` and `WATSONX_PROJECT_ID` from IBM Cloud

### Step 1 — Connect your repo to Render

1. Log in to [dashboard.render.com](https://dashboard.render.com)
2. Click **New → Blueprint**
3. Connect your GitHub account and select this repo
4. Render will detect `render.yaml` and show two services:
   - `drug-safety-backend` (FastAPI)
   - `drug-safety-frontend` (Streamlit)
5. Click **Apply**

### Step 2 — Set secrets (before or after first deploy)

Go to each service → **Environment** tab and set:

**On `drug-safety-backend`:**

| Key | Value |
|---|---|
| `WATSONX_API_KEY` | Your IBM Cloud IAM API key |
| `WATSONX_PROJECT_ID` | Your watsonx.ai project UUID |
| `WATSONX_URL` | `https://us-south.ml.cloud.ibm.com` (or your region) |
| `CORS_ORIGINS` | *(fill in after step 3 — see below)* |

**On `drug-safety-frontend`:**

| Key | Value |
|---|---|
| `BACKEND_URL` | *(fill in after step 3 — see below)* |

### Step 3 — Wire the two services together

After the first deploy finishes, Render assigns permanent URLs like:

```
Backend  →  https://drug-safety-backend.onrender.com
Frontend →  https://drug-safety-frontend.onrender.com
```

Now go back and fill in the two remaining env vars:

- On **`drug-safety-backend`** → `CORS_ORIGINS` = `https://drug-safety-frontend.onrender.com`
- On **`drug-safety-frontend`** → `BACKEND_URL` = `https://drug-safety-backend.onrender.com`

Click **Save Changes** on each — Render redeploys automatically.

### Step 4 — Share the URL

The shareable URL is the **frontend** service URL:
```
https://drug-safety-frontend.onrender.com
```

> **Free tier note:** Render free services spin down after 15 minutes of inactivity.
> The first request after a cold start takes ~30 seconds. Upgrade to the $7/mo Starter
> plan to keep them always-on.

---

## Option B — Docker Compose (local, instant)

Test the containerised build on your own machine before pushing to Render.

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running

### Run

```bash
# From repo root, with src/.env already configured:
docker compose up --build
```

Both services start. Open:
- **UI** → http://localhost:8501
- **API** → http://localhost:8000
- **Swagger** → http://localhost:8000/docs

Stop with `Ctrl+C`, then `docker compose down`.

### Test the build before pushing to Render

```bash
# Build backend image
docker build -f Dockerfile.backend -t drug-safety-backend .

# Build frontend image
docker build -f Dockerfile.frontend -t drug-safety-frontend .
```

If both build without errors, the Render deploy will succeed.

---

## Option C — Railway (alternative to Render)

[Railway](https://railway.app) also supports Docker deploys.

1. Create a new project → **Deploy from GitHub**
2. Add two services from the same repo, setting **Dockerfile Path** to
   `Dockerfile.backend` and `Dockerfile.frontend` respectively
3. Set the same env vars as in Option A Step 2
4. Set `BACKEND_URL` on the frontend service to the Railway URL of the backend

---

## Environment variables reference

| Variable | Service | Required | Description |
|---|---|---|---|
| `WATSONX_API_KEY` | backend | Yes (for LLM) | IBM Cloud IAM API key |
| `WATSONX_PROJECT_ID` | backend | Yes (for LLM) | watsonx.ai project UUID |
| `WATSONX_URL` | backend | Yes (for LLM) | Region endpoint e.g. `https://us-south.ml.cloud.ibm.com` |
| `WATSONX_MODEL_ID` | backend | No | Defaults to `meta-llama/llama-3-3-70b-instruct` |
| `CORS_ORIGINS` | backend | Yes (deployed) | Comma-separated list of allowed frontend origins |
| `BACKEND_URL` | frontend | Yes (deployed) | Full URL of the backend service |

> Without `WATSONX_API_KEY` the app still runs — LLM fields show a stub notice.
> Signal Detection and Submission Readiness scoring work fully without it.
