"""
In-memory database layer for prospects, campaigns, and emails.
Uses dictionaries for simplicity — swap to SQLAlchemy/PostgreSQL for production.
"""

from typing import Dict, List, Optional
from datetime import datetime
from app.models import (
    Prospect, Campaign, OutreachEmail, ResearchData,
    CRMRecord, ProspectStatus, CampaignStatus, AnalyticsOverview
)


class Database:
    """Simple in-memory store. Persists for the lifetime of the server process."""

    def __init__(self):
        self.prospects: Dict[str, Prospect] = {}
        self.campaigns: Dict[str, Campaign] = {}
        self.emails: Dict[str, OutreachEmail] = {}
        self.research: Dict[str, ResearchData] = {}
        self.crm_records: Dict[str, CRMRecord] = {}
        self._activity_log: List[Dict] = []

    # ─────────── Prospects ───────────

    def add_prospect(self, prospect: Prospect) -> Prospect:
        self.prospects[prospect.id] = prospect
        self._log_activity("prospect_added", f"Added prospect: {prospect.name} ({prospect.company})")
        return prospect

    def get_prospect(self, prospect_id: str) -> Optional[Prospect]:
        return self.prospects.get(prospect_id)

    def list_prospects(self, status: Optional[ProspectStatus] = None) -> List[Prospect]:
        prospects = list(self.prospects.values())
        if status:
            prospects = [p for p in prospects if p.status == status]
        return sorted(prospects, key=lambda p: p.created_at, reverse=True)

    def update_prospect_status(self, prospect_id: str, status: ProspectStatus) -> Optional[Prospect]:
        prospect = self.prospects.get(prospect_id)
        if prospect:
            prospect.status = status
            prospect.updated_at = datetime.utcnow()
            self._log_activity("status_update", f"{prospect.name} → {status.value}")
        return prospect

    def delete_prospect(self, prospect_id: str) -> bool:
        if prospect_id in self.prospects:
            del self.prospects[prospect_id]
            return True
        return False

    # ─────────── Campaigns ───────────

    def add_campaign(self, campaign: Campaign) -> Campaign:
        self.campaigns[campaign.id] = campaign
        self._log_activity("campaign_created", f"Campaign: {campaign.name}")
        return campaign

    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        return self.campaigns.get(campaign_id)

    def list_campaigns(self) -> List[Campaign]:
        return sorted(self.campaigns.values(), key=lambda c: c.created_at, reverse=True)

    def update_campaign(self, campaign: Campaign) -> Campaign:
        campaign.updated_at = datetime.utcnow()
        self.campaigns[campaign.id] = campaign
        return campaign

    # ─────────── Emails ───────────

    def add_email(self, email: OutreachEmail) -> OutreachEmail:
        self.emails[email.id] = email
        return email

    def get_email(self, email_id: str) -> Optional[OutreachEmail]:
        return self.emails.get(email_id)

    def get_emails_for_prospect(self, prospect_id: str) -> List[OutreachEmail]:
        return [e for e in self.emails.values() if e.prospect_id == prospect_id]

    def get_emails_for_campaign(self, campaign_id: str) -> List[OutreachEmail]:
        return [e for e in self.emails.values() if e.campaign_id == campaign_id]

    # ─────────── Research ───────────

    def save_research(self, research: ResearchData) -> ResearchData:
        self.research[research.prospect_id] = research
        return research

    def get_research(self, prospect_id: str) -> Optional[ResearchData]:
        return self.research.get(prospect_id)

    # ─────────── CRM ───────────

    def save_crm_record(self, record: CRMRecord) -> CRMRecord:
        self.crm_records[record.prospect_id] = record
        return record

    def get_crm_record(self, prospect_id: str) -> Optional[CRMRecord]:
        return self.crm_records.get(prospect_id)

    # ─────────── Analytics ───────────

    def get_analytics(self) -> AnalyticsOverview:
        total_emails = len(self.emails)
        replies = [e for e in self.emails.values() if e.replied_at]
        positive = [e for e in replies if e.reply_sentiment and e.reply_sentiment.value == "positive"]

        return AnalyticsOverview(
            total_prospects=len(self.prospects),
            total_campaigns=len(self.campaigns),
            emails_sent=len([e for e in self.emails.values() if e.sent_at]),
            replies_received=len(replies),
            positive_replies=len(positive),
            response_rate=round(len(replies) / total_emails * 100, 1) if total_emails else 0.0,
            positive_rate=round(len(positive) / len(replies) * 100, 1) if replies else 0.0,
            recent_activity=self._activity_log[-20:]
        )

    # ─────────── Internal ───────────

    def _log_activity(self, event_type: str, description: str):
        self._activity_log.append({
            "type": event_type,
            "description": description,
            "timestamp": datetime.utcnow().isoformat()
        })
        # Keep only last 100 entries
        if len(self._activity_log) > 100:
            self._activity_log = self._activity_log[-100:]


# Global database instance
db = Database()
