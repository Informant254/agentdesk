"""High-level workflows for common trades business tasks."""

from dataclasses import dataclass, field
from typing import Any

from backend.agent.graph import run_agent
from backend.security.audit import audit_logger


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    success: bool
    data: dict[str, Any]
    messages: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class SchedulingWorkflow:
    """Handle job scheduling workflows for trades businesses."""

    async def book_job(
        self,
        user_id: str,
        client_name: str,
        job_title: str,
        job_address: str,
        start_time: str,
        end_time: str,
        description: str = "",
    ) -> WorkflowResult:
        """Book a new job: create in Jobber + add to Google Calendar."""
        prompt = f"""Book a new job with the following details:
- Client: {client_name}
- Job: {job_title}
- Address: {job_address}
- Start: {start_time}
- End: {end_time}
- Notes: {description}

Steps:
1. Create the job in Jobber
2. Create a matching event in Google Calendar
3. Return the job ID and calendar event ID
"""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            audit_logger.log_action(
                user_id=user_id,
                action="book_job",
                tool_name="composite",
                tool_args={"client_name": client_name, "job_title": job_title},
                result={"status": "completed"},
            )
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            audit_logger.log_action(
                user_id=user_id,
                action="book_job",
                tool_name="composite",
                tool_args={"client_name": client_name, "job_title": job_title},
                result={"status": "failed"},
                error=str(e),
            )
            return WorkflowResult(
                success=False,
                data={},
                errors=[str(e)],
            )

    async def reschedule_job(
        self,
        user_id: str,
        job_id: str,
        new_start_time: str,
        new_end_time: str,
        reason: str = "",
    ) -> WorkflowResult:
        """Reschedule an existing job."""
        prompt = f"""Reschedule job {job_id} to:
- New start: {new_start_time}
- New end: {new_end_time}
- Reason: {reason}

Update both Jobber and Google Calendar."""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            audit_logger.log_action(
                user_id=user_id,
                action="reschedule_job",
                tool_name="composite",
                tool_args={"job_id": job_id, "new_start": new_start_time},
                result={"status": "completed"},
            )
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])

    async def get_daily_schedule(
        self,
        user_id: str,
        date: str,
    ) -> WorkflowResult:
        """Get the full schedule for a specific date."""
        prompt = f"""Show me all jobs scheduled for {date}.
Include:
- Job details from Jobber
- Calendar events from Google Calendar
- Travel time between jobs
- Any conflicts or gaps in the schedule"""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])

    async def optimize_day_route(
        self,
        user_id: str,
        date: str,
        starting_location: str,
    ) -> WorkflowResult:
        """Optimize the route for all jobs on a given day."""
        prompt = f"""Optimize the route for {date}.
Starting location: {starting_location}

Steps:
1. Get all jobs scheduled for {date}
2. Get addresses for each job
3. Calculate the optimal route
4. Return the optimized order with travel times"""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])


class InvoiceWorkflow:
    """Handle invoicing workflows for trades businesses."""

    async def create_invoice_from_job(
        self,
        user_id: str,
        job_id: str,
        line_items: list[dict[str, Any]],
        due_days: int = 30,
    ) -> WorkflowResult:
        """Create an invoice from a completed job."""
        prompt = f"""Create an invoice for job {job_id}.
Line items: {line_items}
Payment terms: Net {due_days} days

Steps:
1. Create the invoice in Jobber
2. Set the correct due date
3. Return the invoice details"""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            audit_logger.log_action(
                user_id=user_id,
                action="create_invoice",
                tool_name="composite",
                tool_args={"job_id": job_id},
                result={"status": "completed"},
            )
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])

    async def send_payment_reminder(
        self,
        user_id: str,
        invoice_id: str,
    ) -> WorkflowResult:
        """Send a payment reminder for an overdue invoice."""
        prompt = f"""Send a payment reminder for invoice {invoice_id}.
Use a friendly but professional tone.
Include:
- Invoice amount
- Due date
- Payment methods available"""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])

    async def get_invoice_summary(
        self,
        user_id: str,
    ) -> WorkflowResult:
        """Get a summary of all invoices: paid, pending, overdue."""
        prompt = """Give me an invoice summary:
- Total outstanding
- Overdue invoices (list each)
- Recently paid
- Upcoming due dates

Format as a clear dashboard view."""
        try:
            result = await run_agent(prompt, user_id)
            last_message = result["messages"][-1]
            return WorkflowResult(
                success=True,
                data={"message": last_message.content},
                messages=[last_message.content],
            )
        except Exception as e:
            return WorkflowResult(success=False, data={}, errors=[str(e)])


# Singleton instances
scheduling_workflow = SchedulingWorkflow()
invoice_workflow = InvoiceWorkflow()
