"""Jobber MCP Server - Connect AI agents to Jobber for trades business management."""

from typing import Any

import httpx
from fastmcp import FastMCP

from backend.config import settings

jobber_server = FastMCP(
    "Jobber",
    description="Connect AI agents to Jobber for job scheduling, invoicing, and client management",
)

JOBBER_API = settings.jobber_api_url or "https://api.getjobber.com/api/graphql"


async def _jobber_query(
    query: str,
    variables: dict[str, Any] | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Execute a GraphQL query against the Jobber API."""
    key = api_key or settings.jobber_api_key
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "X-API-KEY": key,
    }
    body: dict[str, Any] = {"query": query}
    if variables:
        body["variables"] = variables

    async with httpx.AsyncClient() as client:
        resp = await client.post(JOBBER_API, headers=headers, json=body)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise Exception(f"Jobber API errors: {data['errors']}")
        return data.get("data", {})


@jobber_server.tool()
async def list_clients(api_key: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    """List clients (customers) in Jobber."""
    query = """
    query ListClients($first: Int) {
        clients(first: $first) {
            edges {
                node {
                    id
                    name
                    email
                    phone
                    address {
                        street
                        city
                        state
                        postalCode
                    }
                }
            }
        }
    }
    """
    data = await _jobber_query(query, {"first": limit}, api_key)
    edges = data.get("clients", {}).get("edges", [])
    return [edge["node"] for edge in edges]


@jobber_server.tool()
async def get_client(client_id: str, api_key: str | None = None) -> dict[str, Any]:
    """Get detailed information about a specific client."""
    query = """
    query GetClient($id: ID!) {
        client(id: $id) {
            id
            name
            email
            phone
            address {
                street
                city
                state
                postalCode
            }
            jobs {
                edges {
                    node {
                        id
                        title
                        status
                        scheduledAt
                    }
                }
            }
            invoices {
                edges {
                    node {
                        id
                        amount
                        status
                        dueDate
                    }
                }
            }
        }
    }
    """
    data = await _jobber_query(query, {"id": client_id}, api_key)
    return data.get("client", {})


@jobber_server.tool()
async def list_jobs(
    api_key: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List jobs, optionally filtered by status (SCHEDULED, IN_PROGRESS, COMPLETED, etc.)."""
    query = """
    query ListJobs($first: Int, $status: JobStatus) {
        jobs(first: $first, status: $status) {
            edges {
                node {
                    id
                    title
                    status
                    scheduledAt
                    client {
                        name
                        phone
                    }
                    address {
                        street
                        city
                        state
                    }
                }
            }
        }
    }
    """
    data = await _jobber_query(query, {"first": limit, "status": status}, api_key)
    edges = data.get("jobs", {}).get("edges", [])
    return [edge["node"] for edge in edges]


@jobber_server.tool()
async def create_job(
    client_id: str,
    title: str,
    scheduled_at: str,
    description: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Create a new job for a client."""
    query = """
    mutation CreateJob($input: CreateJobInput!) {
        createJob(input: $input) {
            job {
                id
                title
                status
                scheduledAt
            }
        }
    }
    """
    input_data: dict[str, Any] = {
        "clientId": client_id,
        "title": title,
        "scheduledAt": scheduled_at,
    }
    if description:
        input_data["description"] = description

    data = await _jobber_query(query, {"input": input_data}, api_key)
    return data.get("createJob", {}).get("job", {})


@jobber_server.tool()
async def update_job(
    job_id: str,
    title: str | None = None,
    scheduled_at: str | None = None,
    status: str | None = None,
    api_key: str | None = None,
) -> dict[str, Any]:
    """Update an existing job."""
    query = """
    mutation UpdateJob($input: UpdateJobInput!) {
        updateJob(input: $input) {
            job {
                id
                title
                status
                scheduledAt
            }
        }
    }
    """
    input_data: dict[str, Any] = {"id": job_id}
    if title:
        input_data["title"] = title
    if scheduled_at:
        input_data["scheduledAt"] = scheduled_at
    if status:
        input_data["status"] = status

    data = await _jobber_query(query, {"input": input_data}, api_key)
    return data.get("updateJob", {}).get("job", {})


@jobber_server.tool()
async def list_invoices(
    api_key: str | None = None,
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List invoices, optionally filtered by status."""
    query = """
    query ListInvoices($first: Int, $status: InvoiceStatus) {
        invoices(first: $first, status: $status) {
            edges {
                node {
                    id
                    amount
                    status
                    dueDate
                    client {
                        name
                        email
                    }
                    job {
                        title
                    }
                }
            }
        }
    }
    """
    data = await _jobber_query(query, {"first": limit, "status": status}, api_key)
    edges = data.get("invoices", {}).get("edges", [])
    return [edge["node"] for edge in edges]


@jobber_server.tool()
async def create_invoice(
    job_id: str,
    line_items: list[dict[str, Any]],
    api_key: str | None = None,
) -> dict[str, Any]:
    """Create an invoice from a job with line items."""
    query = """
    mutation CreateInvoice($input: CreateInvoiceInput!) {
        createInvoice(input: $input) {
            invoice {
                id
                amount
                status
                dueDate
            }
        }
    }
    """
    input_data: dict[str, Any] = {
        "jobId": job_id,
        "lineItems": line_items,
    }
    data = await _jobber_query(query, {"input": input_data}, api_key)
    return data.get("createInvoice", {}).get("invoice", {})


@jobber_server.tool()
async def search_jobs(
    query: str,
    api_key: str | None = None,
) -> list[dict[str, Any]]:
    """Search jobs by title or client name."""
    # Use list_jobs and filter client-side (Jobber doesn't have a search endpoint)
    all_jobs = await list_jobs(api_key=api_key, limit=100)
    query_lower = query.lower()
    return [
        job
        for job in all_jobs
        if query_lower in job.get("title", "").lower()
        or query_lower in job.get("client", {}).get("name", "").lower()
    ]


@jobber_server.resource("jobber://status")
async def jobber_status() -> str:
    """Check Jobber API connection status."""
    return "Jobber MCP server is running. Configure API key to connect to your Jobber account."


if __name__ == "__main__":
    jobber_server.run()
