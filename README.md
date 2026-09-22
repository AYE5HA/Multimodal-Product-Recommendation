# Atelier

Atelier is a multimodal fashion recommendation system for retrieving and composing complete outfits from a product catalog. It combines structured intent extraction, fashion image–text embeddings, typed compatibility graphs, and constraint-aware ranking to produce recommendations that are both relevant and traceable.

## System overview

```text
User prompt / reference image
            │
            ▼
OpenRouter intent planner
            │
            ▼
Hybrid catalog retrieval ── FashionCLIP text/image embeddings
            │
            ▼
Typed outfit graph ── compatibility, occasion, style, color
            │
            ▼
Constraint-aware reranking
            │
            ▼
Recommendations with evidence, scores, and product links
```

The system distinguishes hard constraints—such as color, budget, audience, and exclusions—from soft preferences such as mood or silhouette. When the catalog cannot satisfy a constraint, the API reports the relaxed constraint instead of silently presenting an apparently valid match.

## Components

- `frontend/` — React and Vite recommendation studio.
- `backend/` — Node.js and Express API gateway with validation, CORS, security headers, health aggregation, and stable response contracts.
- `ml/` — FastAPI recommendation service with OpenRouter intent planning, FashionCLIP indexing, hybrid retrieval, typed graph evidence, and evaluation tooling.
- `data/` — product catalog, product images, and curated outfit relationships.

## Retrieval and ranking

1. The query planner converts natural language into positive attributes, hard exclusions, occasion, audience, colors, and budget.
2. FashionCLIP provides fashion-specific text and image representations for catalog retrieval.
3. Sparse lexical retrieval preserves exact catalog terms and rare product attributes.
4. The compatibility graph connects products through curated outfits, attributes, occasions, and compatible item relationships.
5. Candidate outfits are filtered and reranked using semantic relevance, visual similarity, graph compatibility, outfit completeness, and constraint satisfaction.
6. Each result returns score components and graph evidence used to support the recommendation.

## Evaluation

Regression cases cover traditional wedding guestwear, explicit color requests, formal workwear, exclusions, gender constraints, and budget relaxation. The evaluation harness checks result availability, intent evidence, exclusions, required colors, and budget behavior.

```sh
python ml/scripts/ingest_dataset.py
python ml/scripts/preprocess.py
python -m unittest discover -s ml/tests -v
```

## Run

```sh
docker compose up --build
```

The local application exposes the frontend on `5173`, the API on `4000`, and the ML service on `8000`. OpenRouter is configured through environment variables and is not required for deterministic fallback retrieval.

## Technology

React · Node.js · Express · Python · FastAPI · FashionCLIP · OpenRouter · Docker · Railway
