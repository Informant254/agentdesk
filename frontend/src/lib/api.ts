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

// Chat
export const sendChatMessage = (message: string, context?: Record<string, unknown>) =>
  apiFetch("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, context }),
  });

// Alias kept for ChatPanel.tsx compatibility
export const sendMessage = sendChatMessage;

// Workflows
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

export const getRouteMap = (date: string, startingLocation?: string) => {
  const params = new URLSearchParams({ date });
  if (startingLocation) params.set("starting_location", startingLocation);
  return apiFetch(`/api/workflows/route-map/${date}?starting_location=${encodeURIComponent(startingLocation || "")}`);
};

export const reorderRoute = (date: string, jobOrder: string[], startingLocation?: string) =>
  apiFetch(`/api/workflows/route-map/reorder?date=${encodeURIComponent(date)}&job_order=${jobOrder.join(",")}&starting_location=${encodeURIComponent(startingLocation || "")}`, {
    method: "POST",
  });
