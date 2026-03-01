"""
Prospect management API endpoints.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.models import Prospect, ProspectCreate, ProspectStatus
from app.database import db

router = APIRouter(prefix="/api/prospects", tags=["prospects"])


@router.post("", response_model=Prospect)
async def create_prospect(data: ProspectCreate):
    """Create a new prospect."""
    prospect = Prospect(
        name=data.name,
        email=data.email,
        company=data.company,
        title=data.title,
        linkedin_url=data.linkedin_url,
        website=data.website,
        industry=data.industry,
        company_size=data.company_size,
        tags=data.tags,
    )
    return db.add_prospect(prospect)


@router.get("", response_model=List[Prospect])
async def list_prospects(status: Optional[ProspectStatus] = None):
    """List all prospects, optionally filtered by status."""
    return db.list_prospects(status=status)


@router.get("/{prospect_id}", response_model=Prospect)
async def get_prospect(prospect_id: str):
    """Get a specific prospect by ID."""
    prospect = db.get_prospect(prospect_id)
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
    return prospect


@router.delete("/{prospect_id}")
async def delete_prospect(prospect_id: str):
    """Delete a prospect."""
    if not db.delete_prospect(prospect_id):
        raise HTTPException(status_code=404, detail="Prospect not found")
    return {"message": "Prospect deleted"}


@router.get("/{prospect_id}/research")
async def get_prospect_research(prospect_id: str):
    """Get research data for a prospect."""
    research = db.get_research(prospect_id)
    if not research:
        raise HTTPException(status_code=404, detail="No research data found")
    return research


@router.get("/{prospect_id}/emails")
async def get_prospect_emails(prospect_id: str):
    """Get all emails sent to a prospect."""
    return db.get_emails_for_prospect(prospect_id)
