"""
Gmail Agent — sends outreach emails via Gmail API.
Handles delivery, thread tracking, and error recovery.
"""

from typing import Dict, Any
from datetime import datetime
from app.models import ProspectStatus
from app.tools.gmail import gmail_tool
from app.database import db
from app.memory import memory


async def gmail_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Send the generated email via Gmail.
    
    - Sends the email through Gmail API (or mock)
    - Tracks message and thread IDs for reply monitoring
    - Updates prospect status and database
    """
    prospect_data = state["prospect"]
    email_data = state.get("email", {})
    errors = state.get("errors", [])
    should_send = state.get("should_send", True)

    if not should_send:
        print(f"⏸️  Email sending skipped (should_send=False)")
        return {
            **state,
            "current_step": "send_skipped",
        }

    if not email_data:
        error_msg = "No email to send — email generation may have failed"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "send_failed",
        }

    print(f"\n📤 Sending email to: {prospect_data['email']}...")

    try:
        # Send via Gmail
        result = await gmail_tool.send_email(
            to=prospect_data["email"],
            subject=email_data.get("subject", ""),
            body=email_data.get("body", "")
        )

        if result.get("success"):
            # Update email record with Gmail IDs
            email_id = email_data.get("id")
            if email_id:
                stored_email = db.get_email(email_id)
                if stored_email:
                    stored_email.gmail_message_id = result.get("message_id")
                    stored_email.gmail_thread_id = result.get("thread_id")
                    stored_email.sent_at = datetime.utcnow()
                    db.emails[email_id] = stored_email

            # Update prospect status
            if prospect_data.get("id"):
                db.update_prospect_status(prospect_data["id"], ProspectStatus.EMAIL_SENT)

            # Update campaign stats
            campaign_id = state.get("campaign_id")
            if campaign_id:
                campaign = db.get_campaign(campaign_id)
                if campaign:
                    campaign.emails_sent += 1
                    db.update_campaign(campaign)

            # Log to memory
            memory.store_interaction(
                f"sent_{email_data.get('id', 'unknown')}",
                f"Sent email to {prospect_data['name']} ({prospect_data['email']}) at {prospect_data['company']}. "
                f"Subject: {email_data.get('subject', '')}",
                {
                    "type": "email_sent",
                    "prospect_id": prospect_data.get("id", ""),
                    "message_id": result.get("message_id", ""),
                    "thread_id": result.get("thread_id", ""),
                }
            )

            print(f"✅ Email sent successfully!")
            print(f"   Message ID: {result.get('message_id', 'N/A')}")
            print(f"   Thread ID: {result.get('thread_id', 'N/A')}")

            return {
                **state,
                "email": {
                    **email_data,
                    "gmail_message_id": result.get("message_id"),
                    "gmail_thread_id": result.get("thread_id"),
                    "sent_at": result.get("sent_at"),
                },
                "current_step": "email_sent",
            }
        else:
            error_msg = f"Gmail send failed: {result.get('error', 'Unknown error')}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
            return {
                **state,
                "errors": errors,
                "current_step": "send_failed",
            }

    except Exception as e:
        error_msg = f"Gmail agent error: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "send_failed",
        }
