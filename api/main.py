"""FastAPI application for Distillgov."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import members, bills, votes, trades

app = FastAPI(
    title="Distillgov API",
    description="Congress, distilled. Access congressional data in a simple, accessible way.",
    version="0.1.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(members.router, prefix="/api/members", tags=["Members"])
app.include_router(bills.router, prefix="/api/bills", tags=["Bills"])
app.include_router(votes.router, prefix="/api/votes", tags=["Votes"])
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"])


@app.get("/")
def root():
    """API root."""
    return {
        "name": "Distillgov API",
        "tagline": "Congress, distilled.",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    """Health check."""
    return {"status": "ok"}
