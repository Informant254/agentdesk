"""Supervisor agent that routes tasks to specialized sub-agents."""

from typing import Annotated, Any, Sequence, Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.config import settings


class SupervisorState(TypedDict):
    """State tracked by the supervisor across the workflow."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    next_step: str | None
    task_complete: bool
    errors: list[str]
    collected_data: dict[str, Any]


SUPERVISOR_PROMPT = """You are the AgentDesk Supervisor — the central coordinator for a trades business AI system.

You have specialized sub-agents you can hand off to:

1. **scheduling** — Manages calendar events, availability checks, rescheduling
2. **booking** — Creates new jobs, assigns technicians, confirms appointments
3. **dispatch** — Assigns technicians to jobs, tracks job status, handles emergencies
4. **invoicing** — Creates invoices, tracks payments, sends reminders, handles disputes
5. **route_optimization** — Optimizes multi-stop routes, estimates drive times
6. **customer_followup** — Sends review requests, maintenance reminders, follow-ups

## How to decide

Analyze the user's message and determine which specialist handles it:

- "Schedule", "book", "appointment", "calendar", "available", "reschedule" → **scheduling** or **booking**
- "Assign", "dispatch", "send someone", "which tech", "emergency" → **dispatch**
- "Invoice", "bill", "payment", "charge", "receipt", "overdue" → **invoicing**
- "Route", "drive time", "optimize stops", "best path", "directions" → **route_optimization**
- "Review", "follow up", "remind", "check in", "maintenance" → **customer_followup**

## Rules

- If the task is straightforward and needs only one specialist, set `next_step` to that specialist name.
- If the task needs multiple steps (e.g., "book a job AND send an invoice"), handle them sequentially — start with the first step.
- If you have enough information from the collected_data to answer directly without a specialist, do so and set `task_complete` to true.
- If you're unsure which specialist to use, ask the user for clarification.
- Never perform specialist work yourself — always delegate.

Set `next_step` to one of: scheduling, booking, dispatch, invoicing, route_optimization, customer_followup, or "finish" if the task is complete."""


def _route_next(state: SupervisorState) -> str:
    """Determine which node to go to next."""
    if state.get("task_complete"):
        return END
    next_step = state.get("next_step")
    if next_step and next_step in (
        "scheduling", "booking", "dispatch", "invoicing",
        "route_optimization", "customer_followup",
    ):
        return next_step
    return "finish"


def _finish(state: SupervisorState) -> dict[str, Any]:
    """Final node — return collected results."""
    return {"messages": state["messages"], "task_complete": True}


def create_supervisor(model_name: str | None = None):
    """Create the supervisor graph with sub-agent routing."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )

    def supervisor_node(state: SupervisorState) -> dict[str, Any]:
        """Supervisor decides which specialist to route to."""
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = model.invoke(messages)

        # Parse the response to determine next_step
        content = response.content
        next_step = None
        for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup", "finish"]:
            if step in content.lower():
                next_step = step
                break

        return {
            "messages": [response],
            "next_step": next_step or "finish",
        }

    # Build graph
    workflow = StateGraph(SupervisorState)

    # Add supervisor node
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("finish", _finish)

    # We'll add sub-agent nodes dynamically after they're created
    workflow.set_entry_point("supervisor")

    # Add conditional routing from supervisor
    workflow.add_conditional_edges(
        "supervisor",
        _route_next,
        {
            "scheduling": "scheduling",
            "booking": "booking",
            "dispatch": "dispatch",
            "invoicing": "invoicing",
            "route_optimization": "route_optimization",
            "customer_followup": "customer_followup",
            END: END,
        },
    )

    # All sub-agents route back to supervisor for next step
    for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"]:
        workflow.add_edge(step, "supervisor")

    return workflow.compile()
