"""Dispatch agent — assigns technicians and tracks job status."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_dispatch_tools


class DispatchState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


DISPATCH_PROMPT = """You are the Dispatch Agent for AgentDesk, a trades business AI.

You handle:
- Assigning technicians to jobs based on skills and proximity
- Tracking job status (pending, in-progress, completed)
- Handling emergency/rush jobs
- Reassigning jobs when a tech calls out
- Communicating with field technicians

## Rules
- Prioritize emergency calls (no heat, gas leak, flooding)
- Consider technician skills (licensed electrician vs apprentice)
- Factor in current workload and drive time
- When reassigning, notify the previous tech
- Always confirm assignment with job ID and tech name

When done, summarize who was assigned where and any urgent flags."""


def create_dispatch_agent(model_name: str | None = None):
    """Create the dispatch sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_dispatch_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: DispatchState) -> dict[str, Any]:
        messages = [SystemMessage(content=DISPATCH_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: DispatchState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(DispatchState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
