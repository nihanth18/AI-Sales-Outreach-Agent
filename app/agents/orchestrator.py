"""
LangGraph Orchestrator — defines the multi-agent pipeline.

Pipeline: Research → Generate Email → Send via Gmail → Update CRM → Track Replies

Supports conditional routing, error handling, and retry logic.
"""

from typing import Dict, Any, TypedDict, Annotated, List, Optional
import operator
import asyncio

from app.agents.research_agent import research_agent
from app.agents.email_agent import email_agent
from app.agents.gmail_agent import gmail_agent
from app.agents.crm_agent import crm_agent
from app.agents.reply_tracker import reply_tracker_agent
from app.models import Prospect, ProspectStatus


# ──────────────── State Schema ────────────────

class PipelineState(TypedDict):
    """State flowing through the LangGraph pipeline."""
    prospect: Dict[str, Any]
    research_data: Optional[Dict[str, Any]]
    email: Optional[Dict[str, Any]]
    campaign_id: Optional[str]
    crm_record: Optional[Dict[str, Any]]
    errors: List[str]
    current_step: str
    should_send: bool
    retry_count: int
    max_retries: int
    tone: str
    metadata: Dict[str, Any]


def create_initial_state(
    prospect: Prospect,
    campaign_id: str = None,
    should_send: bool = True,
    tone: str = "professional"
) -> PipelineState:
    """Create the initial state for the pipeline."""
    return PipelineState(
        prospect=prospect.model_dump(),
        research_data=None,
        email=None,
        campaign_id=campaign_id,
        crm_record=None,
        errors=[],
        current_step="start",
        should_send=should_send,
        retry_count=0,
        max_retries=3,
        tone=tone,
        metadata={}
    )


# ──────────────── Routing Logic ────────────────

def should_continue_after_research(state: PipelineState) -> str:
    """Decide next step after research."""
    if state.get("current_step") == "research_failed":
        if state.get("retry_count", 0) < state.get("max_retries", 3):
            return "retry_research"
        return "handle_error"
    return "generate_email"


def should_continue_after_email(state: PipelineState) -> str:
    """Decide next step after email generation."""
    if state.get("current_step") == "email_failed":
        return "handle_error"
    if state.get("should_send", True):
        return "send_email"
    return "update_crm"


def should_continue_after_send(state: PipelineState) -> str:
    """Decide next step after sending."""
    if state.get("current_step") == "send_failed":
        return "handle_error"
    return "update_crm"


def should_continue_after_crm(state: PipelineState) -> str:
    """Decide next step after CRM update."""
    # Always try to track replies even if CRM failed
    if state.get("email", {}).get("gmail_thread_id"):
        return "track_reply"
    return "complete"


# ──────────────── Error Handler ────────────────

async def handle_error(state: Dict[str, Any]) -> Dict[str, Any]:
    """Handle pipeline errors with logging."""
    errors = state.get("errors", [])
    prospect = state.get("prospect", {})

    print(f"\n❌ Pipeline error for {prospect.get('name', 'unknown')}:")
    for err in errors:
        print(f"   • {err}")

    return {
        **state,
        "current_step": "error",
    }


async def complete_pipeline(state: Dict[str, Any]) -> Dict[str, Any]:
    """Mark pipeline as complete."""
    prospect = state.get("prospect", {})
    print(f"\n🎉 Pipeline complete for: {prospect.get('name', 'unknown')}")
    return {
        **state,
        "current_step": "completed",
    }


# ──────────────── Build Graph ────────────────

def build_pipeline():
    """
    Build the LangGraph state graph for the outreach pipeline.
    Falls back to a simple sequential runner if LangGraph is not available.
    """
    try:
        from langgraph.graph import StateGraph, END

        graph = StateGraph(dict)

        # Add nodes
        graph.add_node("research", research_agent)
        graph.add_node("generate_email", email_agent)
        graph.add_node("send_email", gmail_agent)
        graph.add_node("update_crm", crm_agent)
        graph.add_node("track_reply", reply_tracker_agent)
        graph.add_node("handle_error", handle_error)
        graph.add_node("complete", complete_pipeline)

        # Set entry point
        graph.set_entry_point("research")

        # Add conditional edges
        graph.add_conditional_edges(
            "research",
            should_continue_after_research,
            {
                "generate_email": "generate_email",
                "retry_research": "research",
                "handle_error": "handle_error",
            }
        )

        graph.add_conditional_edges(
            "generate_email",
            should_continue_after_email,
            {
                "send_email": "send_email",
                "update_crm": "update_crm",
                "handle_error": "handle_error",
            }
        )

        graph.add_conditional_edges(
            "send_email",
            should_continue_after_send,
            {
                "update_crm": "update_crm",
                "handle_error": "handle_error",
            }
        )

        graph.add_conditional_edges(
            "update_crm",
            should_continue_after_crm,
            {
                "track_reply": "track_reply",
                "complete": "complete",
            }
        )

        graph.add_edge("track_reply", "complete")
        graph.add_edge("handle_error", END)
        graph.add_edge("complete", END)

        compiled = graph.compile()
        print("✅ LangGraph pipeline compiled successfully")
        return compiled

    except ImportError:
        print("⚠️  LangGraph not available, using sequential fallback")
        return None
    except Exception as e:
        print(f"⚠️  LangGraph compilation failed: {e}, using sequential fallback")
        return None


# ──────────────── Sequential Fallback ────────────────

async def run_pipeline_sequential(state: PipelineState) -> Dict[str, Any]:
    """Run the agent pipeline sequentially (fallback when LangGraph is unavailable)."""
    print("\n" + "="*60)
    print("🚀 STARTING OUTREACH PIPELINE (Sequential Mode)")
    print("="*60)

    # Step 1: Research
    state = await research_agent(state)
    if "failed" in state.get("current_step", ""):
        state = await handle_error(state)
        return state

    # Step 2: Generate Email
    state = await email_agent(state)
    if "failed" in state.get("current_step", ""):
        state = await handle_error(state)
        return state

    # Step 3: Send Email
    if state.get("should_send", True):
        state = await gmail_agent(state)
        if "failed" in state.get("current_step", ""):
            state = await handle_error(state)
            return state

    # Step 4: Update CRM
    state = await crm_agent(state)

    # Step 5: Track Replies
    if state.get("email", {}).get("gmail_thread_id"):
        state = await reply_tracker_agent(state)

    # Complete
    state = await complete_pipeline(state)
    return state


# ──────────────── Main Runner ────────────────

_pipeline = None


def get_pipeline():
    """Get or create the pipeline (lazy init)."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_pipeline()
    return _pipeline


async def run_outreach_pipeline(
    prospect: Prospect,
    campaign_id: str = None,
    should_send: bool = True,
    tone: str = "professional"
) -> Dict[str, Any]:
    """
    Run the full outreach pipeline for a prospect.
    
    Args:
        prospect: The prospect to reach out to
        campaign_id: Optional campaign this outreach belongs to
        should_send: Whether to actually send the email (False = draft only)
        tone: Email tone (professional, casual, consultative, friendly)
    
    Returns:
        Final pipeline state with all results
    """
    state = create_initial_state(prospect, campaign_id, should_send, tone)

    pipeline = get_pipeline()

    if pipeline:
        # Run with LangGraph
        print("\n" + "="*60)
        print("🚀 STARTING OUTREACH PIPELINE (LangGraph)")
        print("="*60)

        try:
            result = None
            async for step in pipeline.astream(state):
                result = step
                # Get the last node's output
                for node_name, node_output in step.items():
                    if isinstance(node_output, dict):
                        result = node_output

            return result if result else state
        except Exception as e:
            print(f"⚠️  LangGraph execution failed: {e}, falling back to sequential")
            return await run_pipeline_sequential(state)
    else:
        # Sequential fallback
        return await run_pipeline_sequential(state)
