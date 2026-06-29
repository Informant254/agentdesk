"""Booking agent — creates new jobs and assigns technicians."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_booking_tools


class BookingState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


BOOKING_PROMPT = """You are the Booking Agent for AgentDesk, a trades business AI.

You handle:
- Creating new jobs in Jobber
- Assigning technicians to jobs
- Confirming appointments with clients
- Collecting job details (scope, address, urgency)

## Rules
- Always get: client name/ID, job title, preferred date/time, site address
- If info is missing, ask for it before booking
- When creating a job, include all relevant details in the description
- Return a clear confirmation with job ID and details
- If a job needs an immediate technician assignment, mention that

When your task is done, summarize the booking result clearly."""


def create_booking_agent(model_name: str | None = None):
    """Create the booking sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_booking_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: BookingState) -> dict[str, Any]:
        messages = [SystemMessage(content=BOOKING_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: BookingState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(BookingState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
