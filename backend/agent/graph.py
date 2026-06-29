"""Main agent graph — supervisor pattern routing to specialized sub-agents."""

from typing import Annotated, Any, Sequence, Literal

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_anthropic import ChatAnthropic
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from backend.config import settings
from backend.agent.scheduling import create_scheduling_agent
from backend.agent.booking import create_booking_agent
from backend.agent.dispatch import create_dispatch_agent
from backend.agent.invoicing import create_invoicing_agent
from backend.agent.route import create_route_agent
from backend.agent.followup import create_followup_agent


class AgentState(TypedDict):
    """State of the agent during workflow execution."""

    messages: Annotated[Sequence[BaseMessage], add_messages]
    user_id: str
    context: dict[str, Any]
    current_step: str
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

Analyze the user's message and set `current_step` to the appropriate specialist:

- "Schedule", "book", "appointment", "calendar", "available", "reschedule" → scheduling or booking
- "Assign", "dispatch", "send someone", "which tech", "emergency" → dispatch
- "Invoice", "bill", "payment", "charge", "receipt", "overdue" → invoicing
- "Route", "drive time", "optimize stops", "best path", "directions" → route_optimization
- "Review", "follow up", "remind", "check in", "maintenance" → customer_followup

## Rules

- If the task needs only one specialist, set current_step to that specialist's name.
- If the task needs multiple steps, start with the first one.
- If you have enough information to answer directly, set current_step to "finish".
- Never do specialist work yourself — always delegate.

Available values for current_step: scheduling, booking, dispatch, invoicing, route_optimization, customer_followup, finish"""


def _route_next(state: AgentState) -> str:
    """Determine which node to go to next based on current_step."""
    if state.get("current_step") == "finish":
        return END
    step = state.get("current_step", "")
    if step in (
        "scheduling", "booking", "dispatch", "invoicing",
        "route_optimization", "customer_followup",
    ):
        return step
    return END


def _finish(state: AgentState) -> dict[str, Any]:
    """Return final response from collected_data."""
    collected = state.get("collected_data", {})
    return {"messages": [SystemMessage(content=collected.get("result", "Task completed."))]}


def create_agent(model_name: str | None = None):
    """Create the main agent graph with supervisor + sub-agents."""
    model = ChatAnthropic(
        model=model_name or settings.default_model,
        api_key=settings.anthropic_api_key,
    )

    # Create sub-agents
    scheduling_agent = create_scheduling_agent(model_name)
    booking_agent = create_booking_agent(model_name)
    dispatch_agent = create_dispatch_agent(model_name)
    invoicing_agent = create_invoicing_agent(model_name)
    route_agent = create_route_agent(model_name)
    followup_agent = create_followup_agent(model_name)

    def supervisor_node(state: AgentState) -> dict[str, Any]:
        """Supervisor decides which specialist to route to."""
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = model.invoke(messages)

        content = response.content.lower()
        next_step = "finish"
        for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"]:
            if step in content:
                next_step = step
                break

        return {
            "messages": [response],
            "current_step": next_step,
        }

    def make_sub_agent_node(agent, step_name):
        """Create a node function that runs a sub-agent and returns collected_data."""
        async def sub_agent_node(state: AgentState) -> dict[str, Any]:
            # Run the sub-agent with the user's message
            user_msg = state["messages"][-1].content if state["messages"] else ""
            sub_result = await agent.ainvoke({
                "messages": [HumanMessage(content=user_msg)],
                "user_id": state["user_id"],
                "context": state["context"],
                "result": None,
                "complete": False,
            })

            # Extract the final response from the sub-agent
            final_msg = sub_result["messages"][-1] if sub_result["messages"] else "Done."
            result_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)

            collected = state.get("collected_data", {})
            collected["result"] = result_text
            collected[step_name] = result_text

            return {
                "collected_data": collected,
                "current_step": "finish",  # After sub-agent completes, go to finish
            }

        sub_agent_node.__name__ = f"{step_name}_node"
        return sub_agent_node

    # Build graph
    workflow = StateGraph(AgentState)

    # Add supervisor
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("finish", _finish)

    # Add sub-agent nodes
    workflow.add_node("scheduling", make_sub_agent_node(scheduling_agent, "scheduling"))
    workflow.add_node("booking", make_sub_agent_node(booking_agent, "booking"))
    workflow.add_node("dispatch", make_sub_agent_node(dispatch_agent, "dispatch"))
    workflow.add_node("invoicing", make_sub_agent_node(invoicing_agent, "invoicing"))
    workflow.add_node("route_optimization", make_sub_agent_node(route_agent, "route_optimization"))
    workflow.add_node("customer_followup", make_sub_agent_node(followup_agent, "customer_followup"))

    # Entry point
    workflow.set_entry_point("supervisor")

    # Supervisor routes to sub-agents or finish
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

    # All sub-agents go to finish
    for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"]:
        workflow.add_edge(step, "finish")

    workflow.add_edge("finish", END)

    return workflow.compile()


async def run_agent(
    user_message: str,
    user_id: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run the agent with a user message."""
    agent = create_agent()

    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "context": context or {},
        "current_step": "start",
        "errors": [],
        "collected_data": {},
    }

    result = await agent.ainvoke(initial_state)
    return result
