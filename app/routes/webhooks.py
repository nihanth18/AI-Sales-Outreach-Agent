"""
Webhook endpoints for Gmail push notifications.
"""

from fastapi import APIRouter, Request, HTTPException
import base64
import json

from app.agents.reply_tracker import check_all_pending_replies

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/gmail")
async def gmail_webhook(request: Request):
    """
    Handle Gmail push notification webhooks.
    
    Gmail Cloud Pub/Sub sends notifications when new emails arrive.
    This triggers a reply check for all pending outreach.
    
    Setup: Configure in Google Cloud Console → Pub/Sub → Push Subscription
    """
    try:
        body = await request.json()

        # Decode the Pub/Sub message
        message = body.get("message", {})
        data = message.get("data", "")

        if data:
            decoded = base64.b64decode(data).decode("utf-8")
            notification = json.loads(decoded)
            print(f"📬 Gmail notification: {notification}")

        # Check for new replies
        results = await check_all_pending_replies()

        return {
            "status": "ok",
            "new_replies": len(results)
        }

    except Exception as e:
        print(f"⚠️  Webhook processing failed: {e}")
        # Always return 200 to acknowledge the webhook
        return {"status": "ok", "error": str(e)}


@router.get("/health")
async def webhook_health():
    """Health check for webhook endpoint."""
    return {"status": "healthy", "service": "gmail-webhooks"}
