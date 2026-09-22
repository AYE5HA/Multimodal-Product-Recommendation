# Atelier

Production-oriented monorepo for explainable fashion recommendations.

## Architecture

- `frontend/` — React/Vite studio UI.
- `backend/` — Node 20 Express API gateway with strict Zod validation.
- `ml/` — FastAPI retrieval service. Startup is offline and deterministic: TF-IDF text similarity, optional image colour features, and outfit co-occurrence evidence. An OpenRouter key is optional and never required.
- `data/` — source CSVs and product images. Generated `data/processed/` artifacts are ignored.

## Run locally

```sh
cp .env.example .env
python ml/scripts/ingest_dataset.py
python ml/scripts/preprocess.py
# terminal 1
python -m uvicorn service:app --app-dir ml --port 8000
# terminal 2
cd backend && npm install && npm start
# terminal 3
cd frontend && npm install && npm run dev
```

The UI is at http://localhost:5173, API health is at http://localhost:4000/api/health.

## Docker

`docker compose up --build` starts all three services with correct inter-service paths. No model download is performed during build or startup.
