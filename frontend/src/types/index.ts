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

export interface RouteJob {
  id: string;
  title: string;
  client_name: string;
  address: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  scheduled_at: string;
  estimated_duration_minutes: number;
  lat?: number | null;
  lng?: number | null;
}

export interface RouteLeg {
  distance_m: number;
  distance_text: string;
  duration_s: number;
  duration_text: string;
  start_address: string;
  end_address: string;
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
}

export interface RouteData {
  polyline: string;
  legs: RouteLeg[];
  total_distance_m: number;
  total_distance_km: number;
  total_duration_s: number;
  total_duration_min: number;
}

export interface RouteMapResponse {
  success: boolean;
  starting_location?: string;
  jobs: RouteJob[];
  optimized_order?: RouteJob[];
  route?: RouteData | null;
  total_jobs?: number;
  note?: string;
  error?: string;
}
