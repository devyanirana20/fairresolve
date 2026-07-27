# FairResolve

An explainable AI engine for instant, bilateral dispute resolution — built for American Express Code Street 2026 (Frictionless Dispute & Chargeback Resolution).

This is a real, working implementation of the architecture described in the project proposal: a FastAPI backend with a genuine trained PyTorch model (Captum-explained), a SQLite/Postgres-backed data layer, and a React frontend — not a mockup.

## What this actually does

Maps Amex's own 22 chargeback reason codes into two tiers:

- **Tier 1 — Deterministic (14 codes):** a factual record-match with one correct answer (e.g. was a valid authorization on file). Resolves in under a second, no ML involved.
- **Tier 2 — Fairness-narrative (8 codes):** genuine two-sided disagreements (e.g. item not received) where evidence has to be weighed. A trained PyTorch model scores these, with Captum providing per-feature attribution for every decision, and a confidence gate routes anything ambiguous to a human reviewer instead of guessing.

Both the card member and the merchant see the exact same reasoning — there's no separate, more favorable explanation shown to either side.

## Architecture

```
backend/app/
├── reason_codes.py       # the 22-code taxonomy, tier-tagged
├── models.py             # SQLAlchemy models (card members, merchants, transactions, disputes)
├── database.py           # SQLite by default, swap DATABASE_URL for Postgres
├── evidence_collector.py # Layer 1 — gathers evidence, spaCy NER on free-text intake
├── credibility_engine.py # Layer 2 — bidirectional CE 3.0-style credibility priors
├── weighing_model.py     # Layer 3 — PyTorch model + Captum explainability
├── reasoning_layer.py    # Layer 4 — generates the shared plain-language explanation
├── sla_guardian.py       # Layer 5 — dual FCBA/Reg Z + Amex merchant-clock tracking
├── tier_router.py         # orchestrates all five layers for a single dispute
└── routers/               # FastAPI endpoints

backend/train_model.py     # generates synthetic training data + trains the model
backend/seed_data.py        # seeds the DB with the Case A / Case B worked examples

frontend/src/
├── App.jsx                # main UI — case list, detail view, new-dispute modal
├── api.js                 # API client
└── __tests__/App.test.jsx # integration tests against the real running backend
```

## Running it locally

### Backend

```bash
cd backend
pip install -r requirements.txt
python -m spacy download en_core_web_sm

python train_model.py     # trains the Fair-Weighing Model on synthetic data (~a few seconds)
python seed_data.py        # seeds Case A and Case B through the real pipeline

uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for interactive API documentation.

To run against Postgres instead of SQLite, set `DATABASE_URL` before starting:

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/fairresolve"
```

No model code changes are needed to make that switch — that's the point of the SQLAlchemy ORM layer.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:5173`. Set `VITE_API_BASE` if the backend isn't on `localhost:8000`.

### Tests

Backend logic was verified with direct Python checks and live HTTP requests against the running server (see development notes below). Frontend integration tests run against the **real backend**, not mocks:

```bash
cd frontend
npx vitest run
```

## Honest design notes (things worth knowing, not hiding)

- **PyTorch over a gradient-boosted alternative (e.g. XGBoost) was a deliberate tradeoff**, not a default. A neural scorer needs more training data to reach the same reliability on a small dataset — `train_model.py`'s synthetic data generation exists specifically to make that training data concrete and inspectable rather than hidden. Captum was chosen to keep explainability consistent with the PyTorch-backed NLP layer (spaCy/Hugging Face).
- **The synthetic training data encodes the actual evidence rules** documented for each reason code (e.g. for 4554, no delivery scan favors the card member) — including deliberately injected ambiguity for patterns that should escalate to a human rather than resolve confidently (see the `repeat_dispute_pattern` feature and Case B).
- **4754 (Local Regulatory/Legal Dispute) never auto-resolves**, regardless of confidence — legal interpretation is treated as structurally out of automation scope by design, not just a low-confidence case.
- **This MVP simplifies Tier 1 resolution direction** (currently always resolves for the card member on a record match) for demo purposes; a production version would resolve in whichever direction the record actually supports.
- Full reason-code-by-reason-code evidence logic is documented in the proposal's Reason Code Coverage appendix.

## Status

Backend: fully implemented and tested (all 5 layers, real trained model, live HTTP-tested API).
Frontend: fully implemented and integration-tested against the real backend.
Not yet done: production deployment (AWS), authentication, live network/merchant API integrations (currently seeded/synthetic data stands in for these, as intended for this stage).
