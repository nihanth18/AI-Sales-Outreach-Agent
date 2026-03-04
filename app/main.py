"""
AI Sales Outreach Agent — FastAPI Application Entry Point

A multi-agent AI system that researches prospects, generates
hyper-personalized outreach emails, sends via Gmail, tracks replies,
and updates CRM autonomously.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.routes import prospects, campaigns, analytics, webhooks
from app.config import settings

# ──────────── Create App ────────────

app = FastAPI(
    title="AI Sales Outreach Agent",
    description=(
        "Multi-agent AI sales automation system that researches prospects, "
        "generates hyper-personalized outreach, sends via Gmail, and updates CRM."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ──────────── CORS ────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────── Routes ────────────

app.include_router(prospects.router)
app.include_router(campaigns.router)
app.include_router(analytics.router)
app.include_router(webhooks.router)


# ──────────── Static Files ────────────

static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ──────────── Root / Dashboard ────────────

@app.get("/")
async def root():
    """Serve the dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "name": "AI Sales Outreach Agent",
        "version": "1.0.0",
        "status": "running",
        "mock_mode": settings.mock_mode,
        "docs": "/docs",
        "dashboard": "Dashboard not found. Ensure static/index.html exists.",
    }


@app.get("/api/status")
async def status():
    """System status and configuration check."""
    return {
        "status": "running",
        "environment": settings.app_env,
        "mock_mode": settings.mock_mode,
        "services": {
            "openai": "configured" if settings.has_openai else "not configured",
            "tavily": "configured" if settings.has_tavily else "not configured",
            "gmail": "configured" if settings.has_gmail else "not configured",
            "airtable": "configured" if settings.has_airtable else "not configured",
        },
    }


# ──────────── Startup ────────────

@app.on_event("startup")
async def startup():
    """Initialize services on startup."""
    print("\n" + "="*60)
    print("🤖 AI Sales Outreach Agent v1.0.0")
    print("="*60)
    print(f"   Environment: {settings.app_env}")
    print(f"   Mock Mode:   {'ON ✅' if settings.mock_mode else 'OFF'}")
    print(f"   OpenAI:      {'✅' if settings.has_openai else '❌ (mock emails)'}")
    print(f"   Tavily:      {'✅' if settings.has_tavily else '❌ (mock research)'}")
    print(f"   Gmail:       {'✅' if settings.has_gmail else '❌ (mock send)'}")
    print(f"   Airtable:    {'✅' if settings.has_airtable else '❌ (mock CRM)'}")
    print("="*60)
    print(f"   Dashboard:   http://localhost:8000")
    print(f"   API Docs:    http://localhost:8000/docs")
    print("="*60 + "\n")

    # Initialize Gmail if configured
    if settings.has_gmail and not settings.mock_mode:
        from app.tools.gmail import gmail_tool
        gmail_tool.authenticate()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
