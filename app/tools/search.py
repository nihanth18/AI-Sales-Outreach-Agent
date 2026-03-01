"""
Tavily search tool for prospect and company research.
Falls back to mock data when API key is not configured.
"""

from typing import List, Dict, Any
from app.config import settings


async def search_company(company_name: str) -> List[Dict[str, Any]]:
    """Search for company information."""
    if settings.mock_mode or not settings.has_tavily:
        return _mock_company_search(company_name)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=f"{company_name} company overview products services",
            search_depth="advanced",
            max_results=5,
            include_answer=True
        )
        results = []
        if response.get("answer"):
            results.append({
                "title": "AI Summary",
                "content": response["answer"],
                "url": "",
                "source": "tavily_answer"
            })
        for r in response.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "source": "tavily"
            })
        return results
    except Exception as e:
        print(f"⚠️  Tavily search failed: {e}")
        return _mock_company_search(company_name)


async def search_prospect(prospect_name: str, company: str) -> List[Dict[str, Any]]:
    """Search for prospect's professional profile and activity."""
    if settings.mock_mode or not settings.has_tavily:
        return _mock_prospect_search(prospect_name, company)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=f"{prospect_name} {company} professional background",
            search_depth="basic",
            max_results=5
        )
        return [
            {
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "source": "tavily"
            }
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"⚠️  Prospect search failed: {e}")
        return _mock_prospect_search(prospect_name, company)


async def search_news(company_name: str) -> List[Dict[str, Any]]:
    """Search for recent company news and announcements."""
    if settings.mock_mode or not settings.has_tavily:
        return _mock_news_search(company_name)

    try:
        from tavily import TavilyClient
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(
            query=f"{company_name} latest news announcements 2024 2025",
            search_depth="basic",
            max_results=5
        )
        return [
            {
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "source": "tavily"
            }
            for r in response.get("results", [])
        ]
    except Exception as e:
        print(f"⚠️  News search failed: {e}")
        return _mock_news_search(company_name)


# ──────────────── Mock Data ────────────────

def _mock_company_search(company: str) -> List[Dict[str, Any]]:
    return [
        {
            "title": f"{company} - Company Overview",
            "content": (
                f"{company} is a fast-growing technology company specializing in innovative SaaS solutions. "
                f"Founded in 2019, the company has raised $15M in Series A funding and serves over 500 enterprise clients. "
                f"Their platform focuses on workflow automation and AI-powered analytics, helping businesses "
                f"reduce operational costs by up to 40%. The company uses a modern tech stack including Python, "
                f"React, and cloud-native infrastructure on AWS."
            ),
            "url": f"https://www.{company.lower().replace(' ', '')}.com",
            "source": "mock"
        },
        {
            "title": f"{company} - Recent Developments",
            "content": (
                f"{company} recently announced a new AI-powered feature that automates customer onboarding. "
                f"The company is expanding into the European market and has opened offices in London and Berlin. "
                f"They are actively hiring for engineering and sales positions."
            ),
            "url": f"https://blog.{company.lower().replace(' ', '')}.com",
            "source": "mock"
        }
    ]


def _mock_prospect_search(name: str, company: str) -> List[Dict[str, Any]]:
    return [
        {
            "title": f"{name} - Professional Profile",
            "content": (
                f"{name} is the VP of Engineering at {company}. With over 12 years of experience "
                f"in software development and team leadership, they have a strong background in "
                f"scaling engineering teams and implementing DevOps best practices. Previously worked "
                f"at Google and Stripe. Active speaker at tech conferences and contributor to open-source projects. "
                f"Known for advocating developer productivity tools and AI-assisted workflows."
            ),
            "url": f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
            "source": "mock"
        }
    ]


def _mock_news_search(company: str) -> List[Dict[str, Any]]:
    return [
        {
            "title": f"{company} Raises Series A Funding",
            "content": (
                f"{company} has announced the closing of a $15M Series A round led by Sequoia Capital. "
                f"The funding will be used to expand the engineering team and accelerate product development. "
                f"CEO states: 'We're focused on building the next generation of AI-powered business tools.'"
            ),
            "url": f"https://techcrunch.com/{company.lower().replace(' ', '-')}-series-a",
            "source": "mock"
        }
    ]
