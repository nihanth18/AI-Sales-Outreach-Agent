"""
Analytics and dashboard data API endpoints.
"""

from fastapi import APIRouter
from typing import List, Dict, Any

from app.models import AnalyticsOverview
from app.database import db
from app.agents.reply_tracker import check_all_pending_replies

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview():
    """Get dashboard analytics overview."""
    return db.get_analytics()


@router.get("/prospects-by-status")
async def prospects_by_status():
    """Get prospect distribution by status."""
    counts = {}
    for prospect in db.prospects.values():
        status = prospect.status.value
        counts[status] = counts.get(status, 0) + 1
    return counts


@router.get("/campaign-performance")
async def campaign_performance():
    """Get performance metrics for all campaigns."""
    campaigns = db.list_campaigns()
    return [
        {
            "id": c.id,
            "name": c.name,
            "status": c.status.value,
            "total": c.total_prospects,
            "sent": c.emails_sent,
            "replies": c.replies_received,
            "positive": c.positive_replies,
            "response_rate": round(c.replies_received / c.emails_sent * 100, 1) if c.emails_sent else 0,
        }
        for c in campaigns
    ]


@router.get("/recent-emails")
async def recent_emails():
    """Get the most recent emails sent."""
    emails = sorted(
        db.emails.values(),
        key=lambda e: e.created_at,
        reverse=True
    )[:20]

    return [
        {
            "id": e.id,
            "prospect_id": e.prospect_id,
            "subject": e.subject,
            "sent_at": e.sent_at.isoformat() if e.sent_at else None,
            "replied": e.replied_at is not None,
            "sentiment": e.reply_sentiment.value if e.reply_sentiment else None,
            "prospect_name": db.get_prospect(e.prospect_id).name if db.get_prospect(e.prospect_id) else "Unknown",
        }
        for e in emails
    ]


@router.post("/check-replies")
async def trigger_reply_check():
    """Manually trigger a check for new replies across all sent emails."""
    results = await check_all_pending_replies()
    return {
        "checked": len(db.emails),
        "new_replies": len(results),
        "results": results
    }


@router.get("/activity-feed")
async def activity_feed():
    """Get the recent activity feed."""
    analytics = db.get_analytics()
    return analytics.recent_activity
