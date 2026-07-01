"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Calendar, ChevronLeft, ChevronRight,
  MapPin, Clock, User, Loader2, AlertCircle, Plus,
} from "lucide-react";
import { getScheduleJobs, bookJob, type Job } from "@/lib/api";

function formatDateKey(d: Date) {
  return d.toISOString().split("T")[0]; // YYYY-MM-DD
}

function formatTime(iso: string) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

function formatDuration(minutes: number) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (h === 0) return `${m}m`;
  if (m === 0) return `${h}h`;
  return `${h}h ${m}m`;
}

const STATUS_STYLES: Record<string, string> = {
  scheduled: "bg-blue-100 text-blue-700",
  in_progress: "bg-yellow-100 text-yellow-700",
  completed: "bg-green-100 text-green-700",
  cancelled: "bg-slate-100 text-slate-500",
};

interface BookingForm {
  client_name: string;
  job_title: string;
  job_address: string;
  date: string;
  time: string;
  duration_minutes: number;
  description: string;
}

export function SchedulePanel() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showBookingForm, setShowBookingForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<BookingForm>({
    client_name: "",
    job_title: "",
    job_address: "",
    date: formatDateKey(new Date()),
    time: "09:00",
    duration_minutes: 60,
    description: "",
  });

  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getScheduleJobs(formatDateKey(selectedDate));
      setJobs(res.jobs ?? []);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load schedule");
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => { fetchJobs(); }, [fetchJobs]);

  const handleBook = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const scheduled_at = new Date(`${form.date}T${form.time}:00`).toISOString();
      await bookJob({
        client_name: form.client_name,
        job_title: form.job_title,
        job_address: form.job_address,
        scheduled_at,
        estimated_duration_minutes: form.duration_minutes,
        description: form.description,
      });
      setShowBookingForm(false);
      setForm({ client_name: "", job_title: "", job_address: "", date: formatDateKey(selectedDate), time: "09:00", duration_minutes: 60, description: "" });
      await fetchJobs();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to book job");
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });

  const navigateDate = (offset: number) => {
    setSelectedDate(prev => {
      const next = new Date(prev);
      next.setDate(next.getDate() + offset);
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Schedule</h2>
          <p className="text-sm text-slate-500">{formatDate(selectedDate)}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => navigateDate(-1)} className="p-2 hover:bg-slate-100 rounded-lg">
            <ChevronLeft size={20} />
          </button>
          <button onClick={() => setSelectedDate(new Date())} className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 rounded-lg">
            Today
          </button>
          <button onClick={() => navigateDate(1)} className="p-2 hover:bg-slate-100 rounded-lg">
            <ChevronRight size={20} />
          </button>
          <button
            onClick={() => setShowBookingForm(v => !v)}
            className="ml-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-1.5"
          >
            <Plus size={16} />
            Book Job
          </button>
        </div>
      </div>

      {/* Booking Form */}
      {showBookingForm && (
        <div className="p-4 bg-blue-50 border-b border-blue-200">
          <h3 className="font-semibold text-slate-800 mb-3">New Job</h3>
          <form onSubmit={handleBook} className="grid grid-cols-2 gap-3">
            <input required className="col-span-2 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Client name" value={form.client_name} onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))} />
            <input required className="col-span-2 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Job title (e.g. AC Repair)" value={form.job_title} onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))} />
            <input required className="col-span-2 px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="Job address" value={form.job_address} onChange={e => setForm(f => ({ ...f, job_address: e.target.value }))} />
            <div>
              <label className="block text-xs text-slate-500 mb-1">Date</label>
              <input type="date" required className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Time</label>
              <input type="time" required className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                value={form.time} onChange={e => setForm(f => ({ ...f, time: e.target.value }))} />
            </div>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Duration (minutes)</label>
              <input type="number" min={15} step={15} className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                value={form.duration_minutes} onChange={e => setForm(f => ({ ...f, duration_minutes: Number(e.target.value) }))} />
            </div>
            <div className="flex items-end gap-2">
              <button type="submit" disabled={submitting}
                className="flex-1 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {submitting ? "Saving…" : "Save Job"}
              </button>
              <button type="button" onClick={() => setShowBookingForm(false)}
                className="px-3 py-2 bg-slate-200 text-slate-700 text-sm rounded-lg hover:bg-slate-300">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Job List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading && (
          <div className="flex items-center justify-center py-16">
            <Loader2 size={28} className="animate-spin text-blue-500" />
          </div>
        )}

        {error && !loading && (
          <div className="flex items-start gap-2 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
            <AlertCircle size={16} className="flex-shrink-0 mt-0.5" />
            <div>
              <p className="font-medium">Failed to load schedule</p>
              <p className="text-xs mt-0.5">{error}</p>
              <button onClick={fetchJobs} className="mt-2 text-xs underline hover:no-underline">Retry</button>
            </div>
          </div>
        )}

        {!loading && !error && jobs.length === 0 && (
          <div className="text-center py-16">
            <Calendar size={48} className="mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 font-medium">No jobs scheduled for this day</p>
            <p className="text-sm text-slate-400 mt-1">Click "Book Job" to add one.</p>
          </div>
        )}

        {!loading && jobs.length > 0 && (
          <div className="space-y-3">
            {jobs.map(job => (
              <div key={job.id} className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${STATUS_STYLES[job.status] ?? "bg-slate-100 text-slate-600"}`}>
                        {job.status.replace("_", " ")}
                      </span>
                    </div>
                    <h3 className="font-semibold text-slate-900">{job.title}</h3>
                    <div className="mt-2 space-y-1 text-sm text-slate-600">
                      <div className="flex items-center gap-2">
                        <User size={14} />
                        {job.client_name}
                      </div>
                      <div className="flex items-center gap-2">
                        <MapPin size={14} />
                        {job.address}
                      </div>
                      <div className="flex items-center gap-2">
                        <Clock size={14} />
                        {formatTime(job.scheduled_at)} ({formatDuration(job.estimated_duration_minutes)})
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer Stats */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-slate-500">Total Jobs:</span>{" "}
            <span className="font-semibold">{jobs.length}</span>
          </div>
          <div>
            <span className="text-slate-500">Scheduled:</span>{" "}
            <span className="font-semibold text-blue-600">
              {jobs.filter(j => j.status === "scheduled").length}
            </span>
          </div>
          <div>
            <span className="text-slate-500">In Progress:</span>{" "}
            <span className="font-semibold text-yellow-600">
              {jobs.filter(j => j.status === "in_progress").length}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Completed:</span>{" "}
            <span className="font-semibold text-green-600">
              {jobs.filter(j => j.status === "completed").length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
