# Atelier

Atelier is a deployable fashion recommendation application that turns natural-language style intent into ranked, complete looks. It combines catalog retrieval with a compatibility graph built from curated outfits, then returns score breakdowns and grounded evidence for every result.

## Stack

- `frontend/` — React 18 and Vite UI for recommendation flow, filters, scores, evidence, and product links.
- `backend/` — Node 20 and Express API gateway with request validation, CORS, security headers, health aggregation, and stable response contracts.
- `ml/` — Python 3.11 and FastAPI ranking service. It uses deterministic TF-IDF retrieval plus outfit co-occurrence graph scoring, so local startup does not download a model.
- `data/` — catalog, curated outfit relationships, and product images.

## Recommendation flow

1. The ingest script validates required columns, row counts, numeric prices, and product references used by outfits.
2. Preprocessing normalizes prices and searchable text and writes ignored local artifacts under `data/processed/`.
3. The ML service ranks complete outfit subgraphs against the query, gender, occasion, and total-look budget.
4. The API returns item metadata, total price, retrieval/graph/structure scores, and evidence strings.
5. If `OPENROUTER_API_KEY` is configured on the ML service, it may rewrite the evidence into a short explanation. Filtering and ranking never depend on the model.

## Local development

Requirements: Node 20+, Python 3.11+, and the dependencies in each package.

```sh
cp .env.example .env
python ml/scripts/ingest_dataset.py
python ml/scripts/preprocess.py

# terminal 1
python -m uvicorn service:app --app-dir ml --port 8000

# terminal 2
npm install --prefix backend
npm start --prefix backend

# terminal 3
npm install --prefix frontend
npm run dev --prefix frontend
```

Open `http://localhost:5173`. API endpoints are available at `http://localhost:4000/api/health`, `POST /api/recommend`, `GET /api/catalog/products`, and `GET /api/catalog/stats`.

## Docker Compose

```sh
docker compose up --build
```

The ML service exposes port 8000, the API 4000, and the frontend 5173. `OPENROUTER_API_KEY` and `OPENROUTER_MODEL` are optional environment variables; the application remains fully functional without them.

## Validation

```sh
python ml/scripts/ingest_dataset.py
python ml/scripts/preprocess.py
python -m py_compile ml/service.py ml/scripts/*.py
npm run build --prefix frontend
```

With the ML service running, `python ml/scripts/smoke_test.py` checks health, filtering, complete outfit assembly, and evidence output.
