"""Tests for agent workflows."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.agent.workflows import (
    SchedulingWorkflow,
    InvoiceWorkflow,
    WorkflowResult,
)


class TestSchedulingWorkflow:
    """Test scheduling workflow."""

    @pytest.mark.asyncio
    async def test_book_job_success(self):
        workflow = SchedulingWorkflow()
        with patch("backend.agent.workflows.run_agent") as mock_run:
            mock_run.return_value = {
                "messages": [type("Msg", (), {"content": "Job booked successfully"})()],
            }
            result = await workflow.book_job(
                user_id="test_user",
                client_name="Test Client",
                job_title="AC Repair",
                job_address="123 Test St",
                start_time="2026-07-01T09:00:00Z",
                end_time="2026-07-01T11:00:00Z",
            )
            assert result.success
            assert "Job booked successfully" in result.messages[0]

    @pytest.mark.asyncio
    async def test_book_job_failure(self):
        workflow = SchedulingWorkflow()
        with patch("backend.agent.workflows.run_agent") as mock_run:
            mock_run.side_effect = Exception("API Error")
            result = await workflow.book_job(
                user_id="test_user",
                client_name="Test Client",
                job_title="AC Repair",
                job_address="123 Test St",
                start_time="2026-07-01T09:00:00Z",
                end_time="2026-07-01T11:00:00Z",
            )
            assert not result.success
            assert len(result.errors) > 0

    @pytest.mark.asyncio
    async def test_get_daily_schedule(self):
        workflow = SchedulingWorkflow()
        with patch("backend.agent.workflows.run_agent") as mock_run:
            mock_run.return_value = {
                "messages": [type("Msg", (), {"content": "Today's schedule: 3 jobs"})()],
            }
            result = await workflow.get_daily_schedule("test_user", "2026-07-01")
            assert result.success


class TestInvoiceWorkflow:
    """Test invoice workflow."""

    @pytest.mark.asyncio
    async def test_create_invoice(self):
        workflow = InvoiceWorkflow()
        with patch("backend.agent.workflows.run_agent") as mock_run:
            mock_run.return_value = {
                "messages": [type("Msg", (), {"content": "Invoice created: INV-001"})()],
            }
            result = await workflow.create_invoice_from_job(
                user_id="test_user",
                job_id="job_123",
                line_items=[{"description": "Labor", "quantity": 2, "unit_price_cents": 50000}],
            )
            assert result.success

    @pytest.mark.asyncio
    async def test_get_invoice_summary(self):
        workflow = InvoiceWorkflow()
        with patch("backend.agent.workflows.run_agent") as mock_run:
            mock_run.return_value = {
                "messages": [type("Msg", (), {"content": "Invoice summary: $5,000 outstanding"})()],
            }
            result = await workflow.get_invoice_summary("test_user")
            assert result.success


class TestWorkflowResult:
    """Test WorkflowResult dataclass."""

    def test_success_result(self):
        result = WorkflowResult(success=True, data={"key": "value"})
        assert result.success
        assert result.errors == []
        assert result.messages == []

    def test_failure_result(self):
        result = WorkflowResult(success=False, data={}, errors=["Something went wrong"])
        assert not result.success
        assert "Something went wrong" in result.errors
