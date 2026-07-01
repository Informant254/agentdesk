const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";

let _token: string | null = null;

export function setAuthToken(token: string) {
  _token = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("agentdesk_token", token);
  }
}

export function getAuthToken(): string | null {
  if (_token) return _token;
  if (typeof window !== "undefined") {
    _token = localStorage.getItem("agentdesk_token");
  }
  return _token;
}

export function clearAuthToken() {
  _token = null;
  if (typeof window !== "undefined") {
    localStorage.removeItem("agentdesk_token");
  }
}

async function apiFetch(path: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string> || {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export const sendChatMessage = (message: string, context?: Record<string, unknown>) =>
  apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, context }),
  });

// Alias for ChatPanel.tsx compatibility
export const sendMessage = sendChatMessage;

// ── Jobs (real DB, no LLM hallucination) ─────────────────────────────────────

export interface Job {
  id: string;
  title: string;
  client_name: string;
  address: string;
  scheduled_at: string;      // ISO-8601
  estimated_duration_minutes: number;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  description?: string;
  address_lat?: number | null;
  address_lng?: number | null;
}

export interface ScheduleResponse {
  jobs: Job[];
  date: string;
  total: number;
}

export const getScheduleJobs = (date: string): Promise<ScheduleResponse> =>
  apiFetch(`/api/jobs/schedule?date=${encodeURIComponent(date)}`);

export const bookJob = (data: {
  client_name: string;
  job_title: string;
  job_address: string;
  scheduled_at: string;
  estimated_duration_minutes?: number;
  description?: string;
}) =>
  apiFetch("/api/jobs/book", { method: "POST", body: JSON.stringify(data) });

// ── Invoices (real DB, no LLM hallucination) ──────────────────────────────────

export interface Invoice {
  id: string;
  client_name: string;
  job_title: string;
  amount_cents: number;
  status: "draft" | "sent" | "paid" | "overdue";
  due_date: string;           // YYYY-MM-DD
  notes?: string;
  created_at?: string;
  paid_at?: string | null;
}

export interface InvoiceListResponse {
  invoices: Invoice[];
  summary: {
    outstanding_cents: number;
    overdue_cents: number;
    paid_this_month_cents: number;
    total: number;
  };
}

export const getInvoiceList = (): Promise<InvoiceListResponse> =>
  apiFetch("/api/invoices/list");

export const createInvoiceDirect = (data: {
  client_name: string;
  job_title: string;
  amount_cents: number;
  status?: string;
  due_date: string;
  notes?: string;
}) =>
  apiFetch("/api/invoices/create", { method: "POST", body: JSON.stringify(data) });

// ── Route Map ─────────────────────────────────────────────────────────────────

export const getRouteMap = (date: string, startingLocation?: string) =>
  apiFetch(`/api/workflows/route-map/${date}?starting_location=${encodeURIComponent(startingLocation || "")}`);

export const reorderRoute = (date: string, jobOrder: string[], startingLocation?: string) =>
  apiFetch(`/api/workflows/route-map/reorder?date=${encodeURIComponent(date)}&job_order=${jobOrder.join(",")}&starting_location=${encodeURIComponent(startingLocation || "")}`, {
    method: "POST",
  });

// ── Legacy workflow helpers (kept for compatibility) ───────────────────────────

export const getDailySchedule = (date: string) =>
  apiFetch(`/api/workflows/daily-schedule/${date}`);

export const optimizeRoute = (date: string, startingLocation: string) =>
  apiFetch(`/api/workflows/optimize-route/${date}?starting_location=${encodeURIComponent(startingLocation)}`);

export const getInvoiceSummary = () =>
  apiFetch("/api/workflows/invoice-summary");

export const createInvoice = (jobId: string, lineItems: unknown[], dueDays = 30) =>
  apiFetch("/api/workflows/create-invoice", {
    method: "POST",
    body: JSON.stringify({ job_id: jobId, line_items: lineItems, due_days: dueDays }),
  });
