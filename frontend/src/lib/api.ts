import type { ApiResponse, ChatMessage, Job, Invoice } from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

let authToken: string | null = null;

export function setAuthToken(token: string) {
  authToken = token;
  if (typeof window !== "undefined") {
    localStorage.setItem("agentdesk_token", token);
  }
}

export function getAuthToken(): string | null {
  if (authToken) return authToken;
  if (typeof window !== "undefined") {
    authToken = localStorage.getItem("agentdesk_token");
  }
  return authToken;
}

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers,
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API request failed");
  }
  return res.json();
}

// Auth
export async function login(email: string, password: string) {
  const data = await apiRequest<{ access_token: string; user_id: string }>(
    "/api/auth/login",
    { method: "POST", body: JSON.stringify({ email, password }) }
  );
  setAuthToken(data.access_token);
  return data;
}

export async function register(
  email: string,
  password: string,
  businessName: string,
  businessType: string
) {
  const data = await apiRequest<{ access_token: string; user_id: string }>(
    "/api/auth/register",
    {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        business_name: businessName,
        business_type: businessType,
      }),
    }
  );
  setAuthToken(data.access_token);
  return data;
}

// Chat
export async function sendMessage(
  message: string,
  context?: Record<string, unknown>
): Promise<ApiResponse<{ response: string }>> {
  return apiRequest("/api/chat", {
    method: "POST",
    body: JSON.stringify({ message, context }),
  });
}

// Jobs
export async function getDailySchedule(
  date: string
): Promise<ApiResponse<{ message: string }>> {
  return apiRequest(`/api/workflows/daily-schedule/${date}`);
}

export async function bookJob(data: {
  client_name: string;
  job_title: string;
  job_address: string;
  start_time: string;
  end_time: string;
  description?: string;
}): Promise<ApiResponse<{ message: string }>> {
  return apiRequest("/api/workflows/book-job", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// Invoices
export async function getInvoiceSummary(): Promise<
  ApiResponse<{ message: string }>
> {
  return apiRequest("/api/workflows/invoice-summary");
}

export async function createInvoice(data: {
  job_id: string;
  line_items: { description: string; quantity: number; unit_price_cents: number }[];
  due_days?: number;
}): Promise<ApiResponse<{ message: string }>> {
  return apiRequest("/api/workflows/create-invoice", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
