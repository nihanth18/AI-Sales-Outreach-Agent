"""
Email Generation Agent — creates hyper-personalized outreach emails
based on research data using OpenAI/LLM.
"""

from typing import Dict, Any
from datetime import datetime
from app.models import OutreachEmail, EmailTone, ProspectStatus
from app.config import settings
from app.memory import memory
from app.database import db


EMAIL_SYSTEM_PROMPT = """You are an expert sales development representative (SDR) writing highly personalized cold outreach emails.

Your emails must:
1. Be concise (under 150 words for the body)
2. Reference specific details about the prospect's company, role, or recent achievements
3. Clearly articulate value without being pushy
4. Include a specific, low-commitment call-to-action
5. Sound human and natural, NOT like a template
6. Never use generic openers like "I hope this email finds you well"

Tone: {tone}

Respond in this exact JSON format:
{{
    "subject": "Email subject line",
    "body": "Full email body text",
    "personalization_notes": ["Note about what was personalized and why"]
}}
"""


async def email_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node: Generate a personalized outreach email.
    
    Uses research data to craft a hyper-personalized email that
    references specific company details, pain points, and the
    prospect's background.
    """
    prospect_data = state["prospect"]
    research_data = state.get("research_data", {})
    campaign_id = state.get("campaign_id")
    errors = state.get("errors", [])

    tone = state.get("tone", "professional")

    print(f"\n✍️  Generating email for: {prospect_data['name']}...")

    try:
        # Build context from research
        context = _build_email_context(prospect_data, research_data)

        # Check vector memory for similar past emails
        similar_emails = memory.search_similar_emails(
            f"{prospect_data['company']} {prospect_data.get('industry', '')}",
            n_results=3
        )
        past_context = ""
        if similar_emails:
            past_context = "\n\nPrevious successful emails for reference (vary your approach):\n"
            for e in similar_emails[:2]:
                past_context += f"- {e['text'][:200]}\n"

        # Generate email using LLM or mock
        if settings.has_openai and not settings.mock_mode:
            email_data = await _generate_with_llm(context, past_context, tone)
        else:
            email_data = _generate_mock_email(prospect_data, research_data, tone)

        # Create email object
        email = OutreachEmail(
            prospect_id=prospect_data.get("id", ""),
            campaign_id=campaign_id,
            subject=email_data["subject"],
            body=email_data["body"],
            tone=EmailTone(tone),
            personalization_notes=email_data.get("personalization_notes", []),
        )

        # Save to database
        db.add_email(email)

        # Store in vector memory
        memory.store_email(
            email.id,
            f"Subject: {email.subject}\nTo: {prospect_data['name']} at {prospect_data['company']}\n\n{email.body}",
            {"prospect_id": prospect_data.get("id", ""), "company": prospect_data["company"]}
        )

        # Update prospect status
        if prospect_data.get("id"):
            db.update_prospect_status(prospect_data["id"], ProspectStatus.EMAIL_DRAFTED)

        print(f"✅ Email generated: \"{email.subject}\"")

        return {
            **state,
            "email": email.model_dump(),
            "current_step": "email_generated",
        }

    except Exception as e:
        error_msg = f"Email generation failed: {str(e)}"
        print(f"❌ {error_msg}")
        errors.append(error_msg)
        return {
            **state,
            "errors": errors,
            "current_step": "email_failed",
        }


def _build_email_context(prospect: Dict, research: Dict) -> str:
    """Build a rich context string for the LLM."""
    parts = [
        f"PROSPECT: {prospect['name']}",
        f"TITLE: {prospect.get('title', 'Unknown')}",
        f"COMPANY: {prospect['company']}",
        f"EMAIL: {prospect['email']}",
    ]

    if prospect.get("industry"):
        parts.append(f"INDUSTRY: {prospect['industry']}")

    if research:
        if research.get("company_info"):
            parts.append(f"\nCOMPANY INFO:\n{research['company_info'][:500]}")
        if research.get("recent_news"):
            parts.append(f"\nRECENT NEWS:\n" + "\n".join(research["recent_news"][:3]))
        if research.get("tech_stack"):
            parts.append(f"\nTECH STACK: {', '.join(research['tech_stack'])}")
        if research.get("pain_points"):
            parts.append(f"\nPAIN POINTS: {', '.join(research['pain_points'])}")
        if research.get("key_insights"):
            parts.append(f"\nKEY INSIGHTS:\n" + "\n".join(research["key_insights"][:3]))
        if research.get("funding_info"):
            parts.append(f"\nFUNDING: {research['funding_info'][:200]}")

    return "\n".join(parts)


async def _generate_with_llm(context: str, past_context: str, tone: str) -> Dict[str, Any]:
    """Generate email using OpenAI."""
    import json
    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)

    response = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {
                "role": "system",
                "content": EMAIL_SYSTEM_PROMPT.format(tone=tone)
            },
            {
                "role": "user",
                "content": f"Write a personalized outreach email based on this research:\n\n{context}{past_context}"
            }
        ],
        temperature=0.7,
        max_tokens=500,
        response_format={"type": "json_object"}
    )

    result = json.loads(response.choices[0].message.content)
    return result


def _generate_mock_email(prospect: Dict, research: Dict, tone: str) -> Dict[str, Any]:
    """Generate a realistic mock email for development."""
    name = prospect["name"]
    company = prospect["company"]
    first_name = name.split()[0] if name else "there"

    # Use research data if available
    tech_mention = ""
    pain_mention = ""
    news_mention = ""

    if research:
        tech = research.get("tech_stack", [])
        if tech:
            tech_mention = f"I noticed your team is working with {tech[0]}"
            if len(tech) > 1:
                tech_mention += f" and {tech[1]}"
            tech_mention += ". "

        pains = research.get("pain_points", [])
        if pains:
            pain_mention = f"Many teams like yours face {pains[0].lower()}. "

        news = research.get("recent_news", [])
        if news:
            news_mention = f"Congrats on the recent developments — {news[0][:80]}. "

    tones = {
        "professional": {
            "subject": f"Helping {company} scale with AI-powered automation",
            "greeting": f"Hi {first_name},",
            "opener": news_mention or f"I've been following {company}'s growth and I'm impressed by what your team has built. ",
            "body": (
                f"{tech_mention}"
                f"{pain_mention}"
                f"We've helped similar companies reduce manual workflows by 60% using our AI automation platform. "
                f"Companies like Stripe and Notion have seen measurable ROI within the first month."
            ),
            "cta": "Would you be open to a quick 15-minute call this week to explore if this could be valuable for your team?",
            "sign_off": "Best regards"
        },
        "casual": {
            "subject": f"Quick idea for {company} 💡",
            "greeting": f"Hey {first_name}!",
            "opener": news_mention or f"Been checking out what {company} is doing — really cool stuff. ",
            "body": (
                f"{tech_mention}"
                f"{pain_mention}"
                f"We built something that might save your team a ton of time on repetitive workflows. "
                f"Think of it as autopilot for the boring stuff."
            ),
            "cta": "Worth a quick chat? Happy to show you a demo whenever works for you.",
            "sign_off": "Cheers"
        },
        "consultative": {
            "subject": f"Thoughts on {company}'s operational efficiency",
            "greeting": f"Hi {first_name},",
            "opener": news_mention or f"I've been studying how companies in your space are approaching operational challenges. ",
            "body": (
                f"{tech_mention}"
                f"{pain_mention}"
                f"Based on my research, I identified three areas where {company} could potentially see significant efficiency gains. "
                f"I put together a brief analysis that might be useful for your team's planning."
            ),
            "cta": "Would it be helpful if I shared this analysis? I'm happy to walk through it in a brief call.",
            "sign_off": "Looking forward to connecting"
        }
    }

    template = tones.get(tone, tones["professional"])

    full_body = (
        f"{template['greeting']}\n\n"
        f"{template['opener']}"
        f"{template['body']}\n\n"
        f"{template['cta']}\n\n"
        f"{template['sign_off']}"
    )

    return {
        "subject": template["subject"],
        "body": full_body,
        "personalization_notes": [
            f"Referenced {company}'s tech stack" if tech_mention else "Used company name",
            f"Addressed pain point" if pain_mention else "General value proposition",
            f"Referenced recent news" if news_mention else "Standard opener",
            f"Tone: {tone}"
        ]
    }
