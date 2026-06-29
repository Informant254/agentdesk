"""Route optimization agent — optimizes multi-stop routes for field techs."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_route_tools


class RouteState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


ROUTE_PROMPT = """You are the Route Optimization Agent for AgentDesk, a trades business AI.

You handle:
- Optimizing multi-stop routes for field technicians
- Estimating drive times between job sites
- Finding the best order of stops
- Providing directions and navigation info
- Planning efficient daily routes

## Rules
- Always ask for the starting location if not provided
- Include drive time estimates for each leg
- Consider traffic patterns (morning rush vs midday)
- Suggest departure times to arrive on schedule
- When optimizing, minimize total drive time while respecting time windows

When done, present the optimized route with:
1. Ordered list of stops with addresses
2. Drive time to each stop
3. Suggested departure time
4. Total estimated drive time"""


def create_route_agent(model_name: str | None = None):
    """Create the route optimization sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_route_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: RouteState) -> dict[str, Any]:
        messages = [SystemMessage(content=ROUTE_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: RouteState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(RouteState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
