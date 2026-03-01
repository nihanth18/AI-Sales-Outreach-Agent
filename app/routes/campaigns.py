"""
Campaign management and execution API endpoints.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import asyncio

from app.models import (
    Campaign, CampaignCreate, CampaignLaunch, CampaignStatus,
    Prospect, EmailTone
)
from app.database import db
from app.agents.orchestrator import run_outreach_pipeline

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=Campaign)
async def create_campaign(data: CampaignCreate):
    """Create a new campaign."""
    campaign = Campaign(
        name=data.name,
        description=data.description,
        tone=data.tone,
        prospect_ids=data.prospect_ids,
        total_prospects=len(data.prospect_ids),
    )
    return db.add_campaign(campaign)


@router.get("", response_model=List[Campaign])
async def list_campaigns():
    """List all campaigns."""
    return db.list_campaigns()


@router.get("/{campaign_id}", response_model=Campaign)
async def get_campaign(campaign_id: str):
    """Get campaign details and stats."""
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.post("/{campaign_id}/launch")
async def launch_campaign(campaign_id: str, background_tasks: BackgroundTasks):
    """
    Launch a campaign — runs the full agent pipeline for each prospect.
    Executes in the background so the API returns immediately.
    """
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Campaign is already running")

    if not campaign.prospect_ids:
        raise HTTPException(status_code=400, detail="No prospects in campaign")

    # Update status
    campaign.status = CampaignStatus.RUNNING
    db.update_campaign(campaign)

    # Run pipeline in background
    background_tasks.add_task(_execute_campaign, campaign)

    return {
        "message": f"Campaign '{campaign.name}' launched with {len(campaign.prospect_ids)} prospects",
        "campaign_id": campaign.id,
        "status": "running"
    }


@router.post("/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a running campaign."""
    campaign = db.get_campaign(campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    campaign.status = CampaignStatus.PAUSED
    db.update_campaign(campaign)
    return {"message": "Campaign paused", "status": "paused"}


@router.get("/{campaign_id}/emails")
async def get_campaign_emails(campaign_id: str):
    """Get all emails in a campaign."""
    return db.get_emails_for_campaign(campaign_id)


@router.post("/quick-outreach")
async def quick_outreach(
    name: str,
    email: str,
    company: str,
    title: str = "",
    tone: str = "professional",
    send: bool = True,
    background_tasks: BackgroundTasks = None
):
    """
    Quick one-off outreach to a single prospect.
    Creates the prospect and runs the full pipeline immediately.
    """
    # Create prospect
    prospect = Prospect(
        name=name,
        email=email,
        company=company,
        title=title,
    )
    db.add_prospect(prospect)

    # Run pipeline
    result = await run_outreach_pipeline(
        prospect=prospect,
        should_send=send,
        tone=tone
    )

    return {
        "message": "Outreach pipeline completed",
        "prospect_id": prospect.id,
        "status": result.get("current_step", "unknown"),
        "email_subject": result.get("email", {}).get("subject", ""),
        "errors": result.get("errors", []),
    }


# ──────────── Background Task ────────────

async def _execute_campaign(campaign: Campaign):
    """Execute the agent pipeline for each prospect in a campaign."""
    print(f"\n{'='*60}")
    print(f"🚀 EXECUTING CAMPAIGN: {campaign.name}")
    print(f"   Prospects: {len(campaign.prospect_ids)}")
    print(f"{'='*60}")

    for i, prospect_id in enumerate(campaign.prospect_ids):
        # Check if campaign was paused
        current = db.get_campaign(campaign.id)
        if current and current.status == CampaignStatus.PAUSED:
            print(f"\n⏸️  Campaign paused after {i} prospects")
            return

        prospect = db.get_prospect(prospect_id)
        if not prospect:
            print(f"⚠️  Prospect {prospect_id} not found, skipping")
            continue

        print(f"\n── Prospect {i+1}/{len(campaign.prospect_ids)}: {prospect.name} ──")

        try:
            await run_outreach_pipeline(
                prospect=prospect,
                campaign_id=campaign.id,
                should_send=True,
                tone=campaign.tone.value
            )
        except Exception as e:
            print(f"❌ Pipeline failed for {prospect.name}: {e}")

        # Small delay between prospects to avoid rate limiting
        if i < len(campaign.prospect_ids) - 1:
            await asyncio.sleep(2)

    # Mark campaign as completed
    campaign = db.get_campaign(campaign.id)
    if campaign:
        from datetime import datetime
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.utcnow()
        db.update_campaign(campaign)

    print(f"\n{'='*60}")
    print(f"✅ CAMPAIGN COMPLETE: {campaign.name}")
    print(f"{'='*60}")
