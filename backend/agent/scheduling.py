"""Scheduling agent — manages calendar events and availability."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_scheduling_tools


class SchedulingState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


SCHEDULING_PROMPT = """You are the Scheduling Agent for AgentDesk, a trades business AI.

You handle:
- Checking technician availability on a calendar
- Booking new jobs (creating calendar events)
- Rescheduling existing appointments
- Viewing daily/weekly schedules
- Finding open time slots

## Rules
- Always confirm details (date, time, technician, job type) before booking
- Check for conflicts before creating events
- Consider travel time between jobs (at least 30 min buffer)
- When done, return a clear summary of what was scheduled or found
- If you need more info from the user, ask via your response (don't call tools yet)

When your task is done, your final response should summarize the result clearly."""


def create_scheduling_agent(model_name: str | None = None):
    """Create the scheduling sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_scheduling_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: SchedulingState) -> dict[str, Any]:
        messages = [SystemMessage(content=SCHEDULING_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: SchedulingState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(SchedulingState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
