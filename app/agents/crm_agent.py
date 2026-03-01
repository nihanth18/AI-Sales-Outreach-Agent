"""
CRM Agent — updates Notion/Airtable with prospect status and outreach history.
"""

from typing import Dict, Any
from datetime import datetime, timedelta
from app.models import CRMRecord
from app.tools.crm import notion_crm
from app.database import db


async def crm_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Update CRM with prospect data and outreach status.
    
    - Creates or updates prospect page in Notion
    - Tracks pipeline stage and outreach history
    - Schedules follow-up reminders
    """
    prospect_data = state["prospect"]
    email_data = state.get("email", {})
    research_data = state.get("research_data", {})
    errors = state.get("errors", [])

    print(f"\n📋 Updating CRM for: {prospect_data['name']}...")

    try:
        # Check if prospect already has a CRM record
        existing_record = db.get_crm_record(prospect_data.get("id", ""))

        if existing_record and existing_record.notion_page_id:
            # Update existing record
            status = _determine_crm_status(state)
            notes = _build_notes(state)

            result = await notion_crm.update_prospect_status(
                page_id=existing_record.notion_page_id,
                status=status,
                notes=notes
            )

            existing_record.status = state["prospect"].get("status", existing_record.status)
            existing_record.last_contacted = datetime.utcnow()
            existing_record.next_follow_up = datetime.utcnow() + timedelta(days=3)
            existing_record.notes.append(notes)
            db.save_crm_record(existing_record)

            print(f"✅ CRM updated: {status}")
        else:
            # Create new prospect page in Notion
            notes = _build_notes(state)
            result = await notion_crm.create_prospect_page(
                name=prospect_data["name"],
                email=prospect_data["email"],
                company=prospect_data["company"],
                status=_determine_crm_status(state),
                title=prospect_data.get("title", ""),
                notes=notes
            )

            # Save CRM record locally
            crm_record = CRMRecord(
                prospect_id=prospect_data.get("id", ""),
                notion_page_id=result.get("page_id"),
                status=prospect_data.get("status", "new"),
                last_contacted=datetime.utcnow() if email_data.get("sent_at") else None,
                next_follow_up=datetime.utcnow() + timedelta(days=3),
                notes=[notes],
                pipeline_stage="outreach"
            )
            db.save_crm_record(crm_record)

            print(f"✅ CRM record created: {result.get('page_id', 'N/A')}")

        return {
            **state,
            "crm_record": db.get_crm_record(prospect_data.get("id", "")).model_dump() if db.get_crm_record(prospect_data.get("id", "")) else None,
            "current_step": "crm_updated",
        }

    except Exception as e:
        error_msg = f"CRM update failed: {str(e)}"
        print(f"⚠️  {error_msg} (non-fatal, continuing)")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "crm_update_failed",
        }


def _determine_crm_status(state: Dict[str, Any]) -> str:
    """Map agent pipeline state to CRM status."""
    step = state.get("current_step", "")
    if "sent" in step:
        return "Outreach Sent"
    elif "email" in step:
        return "Email Drafted"
    elif "research" in step:
        return "Researched"
    elif "replied" in step:
        return "Replied"
    else:
        return "Lead"


def _build_notes(state: Dict[str, Any]) -> str:
    """Build a summary note for the CRM entry."""
    parts = [f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M')}]"]

    email_data = state.get("email", {})
    if email_data.get("subject"):
        parts.append(f"Email: \"{email_data['subject']}\"")

    if email_data.get("sent_at"):
        parts.append("Status: Sent ✅")
    elif email_data.get("subject"):
        parts.append("Status: Drafted")

    research = state.get("research_data", {})
    if research.get("tech_stack"):
        parts.append(f"Tech: {', '.join(research['tech_stack'][:3])}")
    if research.get("pain_points"):
        parts.append(f"Pain: {research['pain_points'][0]}")

    return " | ".join(parts)
