"""Main agent graph — supervisor pattern routing to specialized sub-agents."""

from typing import Annotated, Any, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
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

- "Schedule", "book", "appointment", "calendar", "available", "reschedule" → scheduling or booking
- "Assign", "dispatch", "send someone", "which tech", "emergency" → dispatch
- "Invoice", "bill", "payment", "charge", "receipt", "overdue" → invoicing
- "Route", "drive time", "optimize stops", "best path", "directions" → route_optimization
- "Review", "follow up", "remind", "check in", "maintenance" → customer_followup

If you have enough information to answer directly, set current_step to "finish".
Never do specialist work yourself — always delegate.

Available values for current_step: scheduling, booking, dispatch, invoicing, route_optimization, customer_followup, finish"""


def _make_llm(api_key: str | None = None, provider: str = "anthropic", model_name: str | None = None):
    """Create the best available LLM using the provided key or server defaults."""
    anthropic_key = api_key if provider == "anthropic" else None
    openai_key = api_key if provider == "openai" else None

    # Fall back to server env vars if no user key for this provider
    if not anthropic_key:
        anthropic_key = settings.anthropic_api_key or None
    if not openai_key:
        import os
        openai_key = os.environ.get("OPENAI_API_KEY") or None

    if anthropic_key:
        from langchain_anthropic import ChatAnthropic
        return ChatAnthropic(
            model=model_name or settings.default_model,
            api_key=anthropic_key,
        )

    if openai_key:
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=model_name or "gpt-4o-mini",
            api_key=openai_key,
        )

    raise ValueError(
        "No AI provider key available. "
        "Please add an Anthropic or OpenAI API key in the AI Providers section."
    )


def _route_next(state: AgentState) -> str:
    if state.get("current_step") == "finish":
        return END
    step = state.get("current_step", "")
    if step in ("scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"):
        return step
    return END


def _finish(state: AgentState) -> dict[str, Any]:
    collected = state.get("collected_data", {})
    return {"messages": [SystemMessage(content=collected.get("result", "Task completed."))]}


def create_agent(
    model_name: str | None = None,
    api_key: str | None = None,
    provider: str = "anthropic",
):
    """Create the main agent graph. api_key overrides the server's env key."""
    model = _make_llm(api_key=api_key, provider=provider, model_name=model_name)

    scheduling_agent = create_scheduling_agent(model_name)
    booking_agent = create_booking_agent(model_name)
    dispatch_agent = create_dispatch_agent(model_name)
    invoicing_agent = create_invoicing_agent(model_name)
    route_agent = create_route_agent(model_name)
    followup_agent = create_followup_agent(model_name)

    def supervisor_node(state: AgentState) -> dict[str, Any]:
        messages = [SystemMessage(content=SUPERVISOR_PROMPT)] + list(state["messages"])
        response = model.invoke(messages)
        content = response.content.lower()
        next_step = "finish"
        for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"]:
            if step in content:
                next_step = step
                break
        return {"messages": [response], "current_step": next_step}

    def make_sub_agent_node(agent, step_name):
        async def sub_agent_node(state: AgentState) -> dict[str, Any]:
            user_msg = state["messages"][-1].content if state["messages"] else ""
            sub_result = await agent.ainvoke({
                "messages": [HumanMessage(content=user_msg)],
                "user_id": state["user_id"],
                "context": state["context"],
                "result": None,
                "complete": False,
            })
            final_msg = sub_result["messages"][-1] if sub_result["messages"] else "Done."
            result_text = final_msg.content if hasattr(final_msg, "content") else str(final_msg)
            collected = state.get("collected_data", {})
            collected["result"] = result_text
            collected[step_name] = result_text
            return {"collected_data": collected, "current_step": "finish"}
        sub_agent_node.__name__ = f"{step_name}_node"
        return sub_agent_node

    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("finish", _finish)
    for name, agent in [
        ("scheduling", scheduling_agent),
        ("booking", booking_agent),
        ("dispatch", dispatch_agent),
        ("invoicing", invoicing_agent),
        ("route_optimization", route_agent),
        ("customer_followup", followup_agent),
    ]:
        workflow.add_node(name, make_sub_agent_node(agent, name))

    workflow.set_entry_point("supervisor")
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
    for step in ["scheduling", "booking", "dispatch", "invoicing", "route_optimization", "customer_followup"]:
        workflow.add_edge(step, "finish")
    workflow.add_edge("finish", END)

    return workflow.compile()


async def run_agent(
    user_message: str,
    user_id: str,
    context: dict[str, Any] | None = None,
    api_key: str | None = None,
    provider: str = "anthropic",
) -> dict[str, Any]:
    """Run the agent. api_key + provider select which LLM to use."""
    agent = create_agent(api_key=api_key, provider=provider)
    initial_state: AgentState = {
        "messages": [HumanMessage(content=user_message)],
        "user_id": user_id,
        "context": context or {},
        "current_step": "start",
        "errors": [],
        "collected_data": {},
    }
    return await agent.ainvoke(initial_state)
