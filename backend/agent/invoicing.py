"""Invoicing agent — creates invoices, tracks payments, sends reminders."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.tools import get_invoicing_tools


class InvoicingState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    result: str | None
    complete: bool


INVOICING_PROMPT = """You are the Invoicing Agent for AgentDesk, a trades business AI.

You handle:
- Creating invoices from completed jobs
- Adding line items (labor, parts, permits, etc.)
- Tracking payment status (paid, pending, overdue)
- Sending payment reminders
- Handling invoice disputes and adjustments
- Generating financial summaries

## Rules
- Always create itemized invoices — no lump sums
- Include: job ID, client name, date, line items with quantities and rates
- Set appropriate payment terms (Net 15 for residential, Net 30 for commercial)
- For overdue invoices, be professional but firm in reminders
- When summarizing finances, include total revenue, outstanding, and overdue amounts

When done, clearly state what invoice action was taken and any amounts involved."""


def create_invoicing_agent(model_name: str | None = None):
    """Create the invoicing sub-agent."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )
    tools = get_invoicing_tools()
    model_with_tools = model.bind_tools(tools)

    def agent_node(state: InvoicingState) -> dict[str, Any]:
        messages = [SystemMessage(content=INVOICING_PROMPT)] + list(state["messages"])
        response = model_with_tools.invoke(messages)
        has_tools = hasattr(response, "tool_calls") and response.tool_calls
        return {
            "messages": [response],
            "complete": not has_tools,
        }

    def should_continue(state: InvoicingState) -> str:
        last = state["messages"][-1]
        if hasattr(last, "tool_calls") and last.tool_calls:
            return "tools"
        return END

    workflow = StateGraph(InvoicingState)
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", ToolNode(tools))
    workflow.set_entry_point("agent")
    workflow.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    workflow.add_edge("tools", "agent")

    return workflow.compile()
