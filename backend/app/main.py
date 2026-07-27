"""
FairResolve API — main application entry point.

Run locally:
    uvicorn app.main:app --reload --port 8000

Then visit http://localhost:8000/docs for interactive API documentation.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import disputes, transactions

app = FastAPI(
    title="FairResolve API",
    description="An explainable AI engine for instant, bilateral dispute resolution.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened in production to the actual frontend origin
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(disputes.router)
app.include_router(transactions.router)


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "FairResolve API"}
