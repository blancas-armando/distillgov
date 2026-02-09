"""FastAPI application for Distillgov."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import activity, members, bills, committees, votes, stats

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

# Routers — activity first (recency-first mindset)
app.include_router(activity.router, prefix="/api/activity", tags=["Activity"])
app.include_router(members.router, prefix="/api/members", tags=["Members"])
app.include_router(bills.router, prefix="/api/bills", tags=["Bills"])
app.include_router(committees.router, prefix="/api/committees", tags=["Committees"])
app.include_router(votes.router, prefix="/api/votes", tags=["Votes"])
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])


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
