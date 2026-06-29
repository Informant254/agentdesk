"""Customer follow-up agent — review requests, maintenance reminders, follow-ups."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_followup_tools


class FollowupState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


FOLLOWUP_PROMPT = """You are the Customer Follow-up Agent for AgentDesk, a trades business AI.

You handle:
- Sending review request emails after completed jobs
- Scheduling maintenance reminders (annual HVAC tune-ups, etc.)
- Following up on estimates that haven't been converted to jobs
- Checking in with customers after service
- Managing customer satisfaction surveys

## Rules
- Space out follow-ups — don't spam customers
- Personalize messages with job details and tech name
- For review requests, include a direct link to leave a review
- For maintenance reminders, reference the last service date
- Be warm and professional — this is relationship building
- If a customer had issues, escalate to the business owner

When done, summarize who was contacted and what was sent/scheduled."""


def create_followup_agent(model_name: str | None = None):
    """Create the customer follow-up sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_followup_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: FollowupState) -> dict[str, Any]:
        messages = [SystemMessage(content=FOLLOWUP_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: FollowupState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(FollowupState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
