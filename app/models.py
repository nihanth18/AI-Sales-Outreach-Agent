"""
Pydantic models for the AI Sales Outreach Agent.
Defines all data structures used across agents, API, and storage.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


# ──────────────────────── Enums ────────────────────────

class ProspectStatus(str, Enum):
    NEW = "new"
    RESEARCHED = "researched"
    EMAIL_DRAFTED = "email_drafted"
    EMAIL_SENT = "email_sent"
    REPLIED = "replied"
    FOLLOW_UP = "follow_up"
    CONVERTED = "converted"
    NOT_INTERESTED = "not_interested"


class EmailTone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    CONSULTATIVE = "consultative"
    FRIENDLY = "friendly"


class SentimentType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


# ──────────────────── Core Models ──────────────────────

class Prospect(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: str
    company: str
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    status: ProspectStatus = ProspectStatus.NEW
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    tags: List[str] = Field(default_factory=list)
    custom_fields: Dict[str, Any] = Field(default_factory=dict)


class ResearchData(BaseModel):
    prospect_id: str
    company_info: str = ""
    recent_news: List[str] = Field(default_factory=list)
    tech_stack: List[str] = Field(default_factory=list)
    funding_info: str = ""
    pain_points: List[str] = Field(default_factory=list)
    social_presence: Dict[str, str] = Field(default_factory=dict)
    key_insights: List[str] = Field(default_factory=list)
    raw_search_results: List[Dict[str, Any]] = Field(default_factory=list)
    researched_at: datetime = Field(default_factory=datetime.utcnow)


class OutreachEmail(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    prospect_id: str
    campaign_id: Optional[str] = None
    subject: str = ""
    body: str = ""
    tone: EmailTone = EmailTone.PROFESSIONAL
    personalization_notes: List[str] = Field(default_factory=list)
    gmail_message_id: Optional[str] = None
    gmail_thread_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    reply_sentiment: Optional[SentimentType] = None
    reply_text: Optional[str] = None
    is_follow_up: bool = False
    follow_up_number: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    status: CampaignStatus = CampaignStatus.DRAFT
    tone: EmailTone = EmailTone.PROFESSIONAL
    prospect_ids: List[str] = Field(default_factory=list)
    total_prospects: int = 0
    emails_sent: int = 0
    emails_opened: int = 0
    replies_received: int = 0
    positive_replies: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class CRMRecord(BaseModel):
    prospect_id: str
    airtable_record_id: Optional[str] = None
    status: ProspectStatus = ProspectStatus.NEW
    last_contacted: Optional[datetime] = None
    next_follow_up: Optional[datetime] = None
    notes: List[str] = Field(default_factory=list)
    deal_value: Optional[float] = None
    pipeline_stage: str = "lead"


# ──────────────── Agent State (LangGraph) ──────────────

class AgentState(BaseModel):
    """State passed between LangGraph nodes."""
    prospect: Prospect
    research_data: Optional[ResearchData] = None
    email: Optional[OutreachEmail] = None
    campaign_id: Optional[str] = None
    crm_record: Optional[CRMRecord] = None
    errors: List[str] = Field(default_factory=list)
    current_step: str = "start"
    should_send: bool = True
    retry_count: int = 0
    max_retries: int = 3
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ──────────────── API Request/Response ─────────────────

class ProspectCreate(BaseModel):
    name: str
    email: str
    company: str
    title: Optional[str] = None
    linkedin_url: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class CampaignCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prospect_ids: List[str] = Field(default_factory=list)
    tone: EmailTone = EmailTone.PROFESSIONAL


class CampaignLaunch(BaseModel):
    campaign_id: str


class AnalyticsOverview(BaseModel):
    total_prospects: int = 0
    total_campaigns: int = 0
    emails_sent: int = 0
    replies_received: int = 0
    positive_replies: int = 0
    response_rate: float = 0.0
    positive_rate: float = 0.0
    recent_activity: List[Dict[str, Any]] = Field(default_factory=list)
