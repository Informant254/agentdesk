export interface User {
  id: string;
  email: string;
  business_name: string;
  business_type: string;
}

export interface Job {
  id: string;
  title: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  client_name: string;
  client_phone?: string;
  address: string;
  scheduled_at: string;
  estimated_duration_minutes: number;
}

export interface Invoice {
  id: string;
  job_id?: string;
  amount_cents: number;
  status: "draft" | "sent" | "paid" | "overdue" | "cancelled";
  due_date?: string;
  line_items: LineItem[];
}

export interface LineItem {
  description: string;
  quantity: number;
  unit_price_cents: number;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  errors: string[];
}
