"""
Reply Tracker Agent — monitors Gmail for replies and classifies sentiment.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from app.models import SentimentType, ProspectStatus
from app.tools.gmail import gmail_tool
from app.config import settings
from app.database import db
from app.memory import memory


async def reply_tracker_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Check for replies to sent emails and classify sentiment.
    
    - Checks Gmail thread for replies
    - Classifies reply sentiment (positive/negative/neutral)
    - Updates prospect status and campaign stats
    """
    email_data = state.get("email", {})
    prospect_data = state["prospect"]
    errors = state.get("errors", [])

    thread_id = email_data.get("gmail_thread_id")

    if not thread_id:
        print(f"⏭️  No thread ID to track replies for {prospect_data['name']}")
        return {
            **state,
            "current_step": "tracking_skipped",
        }

    print(f"\n👀 Checking replies for: {prospect_data['name']}...")

    try:
        replies = await gmail_tool.check_replies(thread_id)

        if replies:
            latest_reply = replies[-1]
            reply_text = latest_reply.get("body", latest_reply.get("snippet", ""))

            # Classify sentiment
            sentiment = await _classify_sentiment(reply_text)

            # Update email record
            email_id = email_data.get("id")
            if email_id:
                stored_email = db.get_email(email_id)
                if stored_email:
                    stored_email.replied_at = datetime.utcnow()
                    stored_email.reply_sentiment = sentiment
                    stored_email.reply_text = reply_text[:500]
                    db.emails[email_id] = stored_email

            # Update prospect status
            if prospect_data.get("id"):
                new_status = (
                    ProspectStatus.CONVERTED if sentiment == SentimentType.POSITIVE
                    else ProspectStatus.NOT_INTERESTED if sentiment == SentimentType.NEGATIVE
                    else ProspectStatus.REPLIED
                )
                db.update_prospect_status(prospect_data["id"], new_status)

            # Update campaign stats
            campaign_id = state.get("campaign_id")
            if campaign_id:
                campaign = db.get_campaign(campaign_id)
                if campaign:
                    campaign.replies_received += 1
                    if sentiment == SentimentType.POSITIVE:
                        campaign.positive_replies += 1
                    db.update_campaign(campaign)

            # Log to memory
            memory.store_interaction(
                f"reply_{email_data.get('id', 'unknown')}",
                f"Reply from {prospect_data['name']}: {reply_text[:200]}. Sentiment: {sentiment.value}",
                {
                    "type": "reply_received",
                    "sentiment": sentiment.value,
                    "prospect_id": prospect_data.get("id", ""),
                }
            )

            print(f"✅ Reply detected! Sentiment: {sentiment.value}")
            print(f"   Reply preview: {reply_text[:100]}...")

            return {
                **state,
                "email": {
                    **email_data,
                    "replied_at": datetime.utcnow().isoformat(),
                    "reply_sentiment": sentiment.value,
                    "reply_text": reply_text[:500],
                },
                "current_step": "reply_tracked",
            }
        else:
            print(f"📭 No replies yet for {prospect_data['name']}")
            return {
                **state,
                "current_step": "no_reply",
            }

    except Exception as e:
        error_msg = f"Reply tracking failed: {str(e)}"
        print(f"⚠️  {error_msg}")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "tracking_failed",
        }


async def _classify_sentiment(text: str) -> SentimentType:
    """Classify reply sentiment using LLM or keyword matching."""
    if settings.has_openai and not settings.mock_mode:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=settings.openai_api_key)

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Classify the sentiment of this email reply as exactly one of: "
                            "positive, negative, or neutral. "
                            "Positive = interested, wants to meet/learn more. "
                            "Negative = not interested, unsubscribe, stop emails. "
                            "Neutral = unclear, asking questions, out of office. "
                            "Respond with only one word: positive, negative, or neutral."
                        ),
                    },
                    {"role": "user", "content": text[:500]}
                ],
                temperature=0,
                max_tokens=10,
            )

            result = response.choices[0].message.content.strip().lower()
            if "positive" in result:
                return SentimentType.POSITIVE
            elif "negative" in result:
                return SentimentType.NEGATIVE
            else:
                return SentimentType.NEUTRAL

        except Exception as e:
            print(f"⚠️  LLM sentiment failed, using keyword fallback: {e}")

    # Keyword-based fallback
    return _keyword_sentiment(text)


def _keyword_sentiment(text: str) -> SentimentType:
    """Simple keyword-based sentiment classification."""
    text_lower = text.lower()

    positive_keywords = [
        "interested", "let's chat", "sounds great", "tell me more",
        "schedule", "available", "looking forward", "love to",
        "yes", "absolutely", "great", "excited", "perfect"
    ]
    negative_keywords = [
        "not interested", "unsubscribe", "stop", "remove",
        "no thanks", "don't contact", "not looking", "pass"
    ]

    positive_score = sum(1 for kw in positive_keywords if kw in text_lower)
    negative_score = sum(1 for kw in negative_keywords if kw in text_lower)

    if positive_score > negative_score:
        return SentimentType.POSITIVE
    elif negative_score > positive_score:
        return SentimentType.NEGATIVE
    else:
        return SentimentType.NEUTRAL


async def check_all_pending_replies() -> List[Dict[str, Any]]:
    """Background task: Check replies for all sent emails that haven't been replied to."""
    results = []

    for email_id, email in db.emails.items():
        if email.sent_at and not email.replied_at and email.gmail_thread_id:
            try:
                replies = await gmail_tool.check_replies(email.gmail_thread_id)
                if replies:
                    latest = replies[-1]
                    reply_text = latest.get("body", "")
                    sentiment = await _classify_sentiment(reply_text)

                    email.replied_at = datetime.utcnow()
                    email.reply_sentiment = sentiment
                    email.reply_text = reply_text[:500]
                    db.emails[email_id] = email

                    prospect = db.get_prospect(email.prospect_id)
                    if prospect:
                        db.update_prospect_status(
                            email.prospect_id,
                            ProspectStatus.REPLIED
                        )

                    results.append({
                        "email_id": email_id,
                        "prospect_id": email.prospect_id,
                        "sentiment": sentiment.value,
                        "reply_preview": reply_text[:100]
                    })

            except Exception as e:
                print(f"⚠️  Failed to check reply for {email_id}: {e}")

    return results
