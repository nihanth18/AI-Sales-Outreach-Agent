"""
Research Agent — scrapes company data and researches prospects.
Uses Tavily search to gather company info, news, tech stack, and pain points.
"""

from typing import Dict, Any
from app.models import AgentState, ResearchData, ProspectStatus
from app.tools.search import search_company, search_prospect, search_news
from app.memory import memory
from app.database import db


async def research_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Research a prospect and their company.
    
    Gathers:
    - Company overview and products
    - Recent news and announcements
    - Prospect's professional background
    - Tech stack and pain points
    """
    prospect_data = state["prospect"]
    print(f"\n🔍 Researching: {prospect_data['name']} at {prospect_data['company']}...")

    errors = state.get("errors", [])

    try:
        # Run all searches
        company_results = await search_company(prospect_data["company"])
        prospect_results = await search_prospect(prospect_data["name"], prospect_data["company"])
        news_results = await search_news(prospect_data["company"])

        # Extract and structure research data
        company_info = "\n".join([r["content"] for r in company_results])
        recent_news = [r["content"] for r in news_results]

        # Extract tech stack mentions
        all_text = company_info + " ".join(recent_news)
        tech_keywords = [
            "Python", "JavaScript", "React", "Node.js", "AWS", "Azure", "GCP",
            "Docker", "Kubernetes", "PostgreSQL", "MongoDB", "Redis", "GraphQL",
            "TypeScript", "Go", "Rust", "Java", "Terraform", "microservices",
            "machine learning", "AI", "data pipeline", "CI/CD"
        ]
        tech_stack = [tech for tech in tech_keywords if tech.lower() in all_text.lower()]

        # Identify potential pain points
        pain_keywords = {
            "scaling": "Scaling challenges as the company grows",
            "hiring": "Difficulty in hiring and retaining talent",
            "automation": "Need for better process automation",
            "efficiency": "Looking to improve operational efficiency",
            "integration": "Integration challenges with existing tools",
            "security": "Security and compliance concerns",
            "cost": "Cost optimization and resource management",
        }
        pain_points = [
            desc for keyword, desc in pain_keywords.items()
            if keyword.lower() in all_text.lower()
        ]

        # Build key insights
        key_insights = []
        for r in prospect_results:
            if r["content"]:
                key_insights.append(r["content"][:200])

        # Social presence
        social = {}
        for r in (company_results + prospect_results):
            url = r.get("url", "")
            if "linkedin" in url.lower():
                social["linkedin"] = url
            elif "twitter" in url.lower() or "x.com" in url.lower():
                social["twitter"] = url

        research = ResearchData(
            prospect_id=prospect_data.get("id", ""),
            company_info=company_info,
            recent_news=recent_news,
            tech_stack=tech_stack,
            funding_info=next((r["content"] for r in news_results if "funding" in r.get("content", "").lower()), ""),
            pain_points=pain_points if pain_points else ["General process optimization needs"],
            social_presence=social,
            key_insights=key_insights,
            raw_search_results=company_results + prospect_results + news_results
        )

        # Save to database
        db.save_research(research)

        # Store in vector memory
        research_text = (
            f"Company: {prospect_data['company']}\n"
            f"Prospect: {prospect_data['name']}\n"
            f"Info: {company_info[:500]}\n"
            f"Tech: {', '.join(tech_stack)}\n"
            f"Pain Points: {', '.join(pain_points)}"
        )
        memory.store_research(
            prospect_data.get("id", ""),
            research_text,
            {"company": prospect_data["company"], "name": prospect_data["name"]}
        )

        # Update prospect status
        if prospect_data.get("id"):
            db.update_prospect_status(prospect_data["id"], ProspectStatus.RESEARCHED)

        print(f"✅ Research complete: {len(company_results)} company results, {len(news_results)} news items")
        print(f"   Tech stack: {', '.join(tech_stack) if tech_stack else 'N/A'}")
        print(f"   Pain points: {len(pain_points)} identified")

        return {
            **state,
            "research_data": research.model_dump(),
            "current_step": "research_complete",
        }

    except Exception as e:
        error_msg = f"Research failed: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "research_failed",
        }
