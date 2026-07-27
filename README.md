# ⚖️ FairResolve

> **An explainable AI engine for instant, bilateral dispute resolution.**

Built for **American Express Code Street 2026**  
**Problem Statement:** Frictionless Dispute & Chargeback Resolution

[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?logo=fastapi)]()
[![PyTorch](https://img.shields.io/badge/PyTorch-EE4C2C?logo=pytorch)]()
[![AWS](https://img.shields.io/badge/AWS-Amplify%20%7C%20EC2-FF9900?logo=amazonaws)]()
[![Captum](https://img.shields.io/badge/Captum-Explainable_AI-purple)]()

🌐 **Live Demo:** https://main.dq5kyh0yh0i5r.amplifyapp.com

> **Note:** The frontend is hosted on AWS Amplify. The backend runs on AWS EC2 for cost efficiency and may not be online 24/7. If the demo is temporarily unavailable, screenshots and architecture below demonstrate the complete implementation.

<h2>🎥 Demo</h2>

<p align="center">
  <img src="assets/fairresolve_gif.gif" alt="FairResolve Demo" width="900">
</p>

---

# 🚀 Overview

FairResolve is a **production-style AI dispute resolution platform** that combines deterministic business rules with explainable machine learning to resolve credit card disputes fairly and transparently.

Unlike a prototype or UI mockup, this project contains:

- ✅ Real FastAPI backend
- ✅ Trained PyTorch model
- ✅ Captum explainability
- ✅ SQLAlchemy ORM
- ✅ SQLite / PostgreSQL support
- ✅ React frontend
- ✅ AWS deployment

Every prediction includes a human-readable explanation visible to **both** the cardholder and the merchant.

---

# 🎥 Demo

> *(Add a GIF or 30-second screen recording here.)*

```
Landing Page
↓
Create Dispute
↓
AI Resolution
↓
Feature Attribution
↓
Shared Explanation
```

---

# 🏗 System Architecture

```
                    User
                      │
                      ▼
          React + Vite Frontend
              (AWS Amplify)
                      │
                HTTPS Requests
                      │
                      ▼
            FastAPI Backend (EC2)
                      │
     ┌────────────────┴────────────────┐
     │                                 │
 Evidence Collection             SQLAlchemy ORM
     │                                 │
 Credibility Engine          SQLite / PostgreSQL
     │
 Fair Weighing Model (PyTorch)
     │
 Captum Explainability
     │
 Shared Reasoning Layer
     │
 SLA Guardian
```

---

# ✨ Key Features

- Explainable AI dispute resolution
- Captum feature attribution
- FastAPI REST APIs
- SQLAlchemy ORM
- SQLite / PostgreSQL support
- React frontend
- Synthetic training pipeline
- Rule-based + ML hybrid architecture
- Human confidence escalation
- Shared explanation for both parties
- AWS deployment

---

# 🧠 How FairResolve Works

American Express defines **22 dispute reason codes**.

FairResolve groups them into two categories.

## Tier 1 — Deterministic (14 Codes)

Simple factual verification.

Examples:

- Valid authorization
- Duplicate processing
- Incorrect transaction amount

These disputes resolve instantly using record matching.

No machine learning is involved.

---

## Tier 2 — Fairness Narrative (8 Codes)

Cases requiring judgement.

Examples:

- Item not received
- Service not provided
- Goods not as described

Pipeline:

```
Evidence
      ↓
Credibility Engine
      ↓
PyTorch Fair Weighing Model
      ↓
Captum Feature Attribution
      ↓
Confidence Check
      ↓
Shared Explanation
```

Low-confidence cases automatically escalate to a human reviewer.

---

# 📂 Project Structure

```text
backend/app/
├── reason_codes.py
├── models.py
├── database.py
├── evidence_collector.py
├── credibility_engine.py
├── weighing_model.py
├── reasoning_layer.py
├── sla_guardian.py
├── tier_router.py
└── routers/

backend/
├── train_model.py
└── seed_data.py

frontend/src/
├── App.jsx
├── api.js
└── __tests__/
```

---

# ⚙ Running Locally

## Backend

```bash
cd backend

pip install -r requirements.txt

python -m spacy download en_core_web_sm

python train_model.py

python seed_data.py

uvicorn app.main:app --reload
```

API Docs

```
http://localhost:8000/docs
```

---

### PostgreSQL

```bash
export DATABASE_URL="postgresql://user:pass@localhost:5432/fairresolve"
```

SQLAlchemy makes switching databases seamless.

---

## Frontend

```bash
cd frontend

npm install

npm run dev
```

```
http://localhost:5173
```

Set

```
VITE_API_BASE
```

if your backend isn't running on localhost.

---

# 🧪 Testing

Frontend integration tests use the **real backend**, not mocked APIs.

```bash
cd frontend

npx vitest run
```

Backend functionality has been verified using:

- Live HTTP requests
- Database validation
- End-to-end pipeline execution
- Python validation scripts

---

# 💡 Engineering Decisions

### Why PyTorch instead of XGBoost?

This was an intentional trade-off.

Using PyTorch allows:

- Captum explainability
- Consistent deep learning ecosystem
- Future NLP expansion

Synthetic data generation exists to make every training assumption transparent and reproducible.

---

### Confidence-aware AI

Rather than forcing uncertain predictions,

FairResolve detects ambiguity and automatically routes difficult disputes to a human reviewer.

The system is designed to **avoid confident mistakes**.

---

### Explainability First

Every decision includes feature attribution.

Both merchants and cardholders receive the **same explanation**, ensuring transparency and fairness.

---

### Legal Safeguards

Reason code **4754 (Local Regulatory / Legal Dispute)**

never auto-resolves.

Legal interpretation always requires human review.

---

# 🚀 Current Status

| Component | Status |
|-----------|--------|
| FastAPI Backend | ✅ Complete |
| React Frontend | ✅ Complete |
| PyTorch Model | ✅ Complete |
| Captum Explainability | ✅ Complete |
| REST APIs | ✅ Complete |
| Integration Testing | ✅ Complete |
| AWS Deployment | ✅ Complete |
| Authentication | 🚧 Planned |
| Merchant Integrations | 🚧 Planned |
| Production APIs | 🚧 Planned |

---

# 🔮 Future Improvements

- Authentication & authorisation
- Live payment gateway integrations
- Merchant APIs
- Docker deployment
- CI/CD with GitHub Actions
- Kubernetes deployment
- Real transaction ingestion
- Continuous model retraining

---

# 👩‍💻 Author

**Devyani Rana**

B.Tech — Artificial Intelligence & Data Science  
National Institute of Technology Delhi

Microsoft SWE Intern • Amazon ML Summer School
