# 🤖 AI Sales Outreach Agent

**A multi-agent AI sales automation system that researches prospects, generates hyper-personalized outreach emails, sends via Gmail, tracks replies, and updates CRM autonomously.**

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🔍 **Company Research** | Scrapes company data, news, tech stack, and pain points via Tavily |
| 👤 **Prospect Research** | Gathers professional background and social presence |
| ✉️ **Personalized Emails** | AI-generated hyper-personalized outreach using OpenAI |
| 📤 **Gmail Integration** | Sends emails via Gmail API with OAuth2 |
| 👀 **Reply Tracking** | Monitors threads, classifies sentiment (positive/neutral/negative) |
| 📋 **CRM Updates** | Auto-updates Notion database with pipeline stages |
| 🧠 **Vector Memory** | ChromaDB stores context for smarter future outreach |
| 🚀 **Campaign Management** | Batch outreach with pause/resume and progress tracking |
| 📊 **Analytics Dashboard** | Real-time stats, activity feed, and performance metrics |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend                     │
│  /api/prospects  /api/campaigns  /api/analytics      │
├──────────────────────┬──────────────────────────────┤
│    LangGraph Agent   │      Vector Memory           │
│    Orchestrator      │      (ChromaDB)              │
├──────┬───────┬───────┼───────┬──────────────────────┤
│Research│Email │Gmail  │Reply  │  CRM Agent           │
│Agent   │Agent │Agent  │Track  │  (Notion)            │
└──────┴───────┴───────┴───────┴──────────────────────┘
```

**Agent Pipeline:** Research → Generate Email → Send via Gmail → Update CRM → Track Replies

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your API keys
```

### 3. Run the Server

```bash
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Open Dashboard

Navigate to **http://localhost:8000** in your browser.

---

## ⚙️ Configuration

### Required API Keys

| Service | Environment Variable | Purpose |
|---------|---------------------|---------|
| OpenAI | `OPENAI_API_KEY` | LLM-powered email generation |
| Tavily | `TAVILY_API_KEY` | Web search for prospect research |
| Gmail | `credentials.json` | OAuth2 for sending emails |
| Notion | `NOTION_API_KEY` | CRM database updates |

> **Note:** The system runs fully in **mock mode** without any API keys configured. Mock mode generates realistic fake data so you can explore all features.

### Mock Mode

Set `MOCK_MODE=true` in `.env` to use simulated data for all services. This is the default for development.

---

## 📁 Project Structure

```
AI Sales Outreach Agent/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py     # LangGraph pipeline
│   │   ├── research_agent.py   # Tavily web research
│   │   ├── email_agent.py      # OpenAI email generation
│   │   ├── gmail_agent.py      # Gmail API send
│   │   ├── crm_agent.py        # Notion CRM updates
│   │   └── reply_tracker.py    # Sentiment-classified replies
│   ├── tools/
│   │   ├── search.py           # Tavily search wrapper
│   │   ├── gmail.py            # Gmail API wrapper
│   │   └── crm.py              # Notion API wrapper
│   ├── routes/
│   │   ├── prospects.py        # Prospect CRUD endpoints
│   │   ├── campaigns.py        # Campaign management
│   │   ├── analytics.py        # Dashboard data
│   │   └── webhooks.py         # Gmail push notifications
│   ├── config.py               # Pydantic settings
│   ├── models.py               # Data models
│   ├── database.py             # In-memory database
│   ├── memory.py               # ChromaDB vector store
│   └── main.py                 # FastAPI entry point
├── static/
│   ├── index.html              # Dashboard UI
│   ├── styles.css              # Premium dark theme
│   └── app.js                  # Frontend logic
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔌 API Endpoints

### Prospects
- `POST /api/prospects` — Create a prospect
- `GET /api/prospects` — List all prospects
- `GET /api/prospects/{id}` — Get prospect details
- `DELETE /api/prospects/{id}` — Delete a prospect

### Campaigns
- `POST /api/campaigns` — Create a campaign
- `POST /api/campaigns/{id}/launch` — Launch a campaign
- `POST /api/campaigns/{id}/pause` — Pause a running campaign
- `POST /api/campaigns/quick-outreach` — One-click outreach

### Analytics
- `GET /api/analytics/overview` — Dashboard stats
- `GET /api/analytics/recent-emails` — Recent email activity
- `POST /api/analytics/check-replies` — Trigger reply check

### System
- `GET /api/status` — Service configuration status
- `GET /docs` — Swagger API documentation

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| **Orchestration** | LangGraph (with sequential fallback) |
| **LLM** | OpenAI GPT-4o-mini |
| **Search** | Tavily API |
| **Email** | Gmail API (OAuth2) |
| **CRM** | Notion API |
| **Vector DB** | ChromaDB |
| **Backend** | FastAPI + Uvicorn |
| **Frontend** | Vanilla HTML/CSS/JS |
| **Database** | In-memory (swap to SQLAlchemy for production) |

---

## 📝 Resume Line

> Built a multi-agent AI sales automation system using LangGraph, OpenAI, and FastAPI that researches prospects via web search, generates hyper-personalized outreach emails, sends via Gmail API, tracks replies with sentiment analysis, and updates CRM autonomously — featuring a real-time analytics dashboard and vector memory for contextual agent recall.

---

## 📄 License

MIT
