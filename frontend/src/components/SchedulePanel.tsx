"use client";

import { useState } from "react";
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  MapPin,
  Clock,
  User,
} from "lucide-react";

interface ScheduledJob {
  id: string;
  title: string;
  client: string;
  address: string;
  time: string;
  duration: string;
  status: "scheduled" | "in_progress" | "completed";
}

const mockJobs: ScheduledJob[] = [
  {
    id: "1",
    title: "AC Unit Repair",
    client: "Johnson Residence",
    address: "123 Oak Street, Austin, TX",
    time: "9:00 AM",
    duration: "2 hours",
    status: "scheduled",
  },
  {
    id: "2",
    title: "Furnace Inspection",
    client: "Smith Commercial",
    address: "456 Business Blvd, Austin, TX",
    time: "1:00 PM",
    duration: "1.5 hours",
    status: "scheduled",
  },
  {
    id: "3",
    title: "Emergency Pipe Burst",
    client: "Williams Home",
    address: "789 Maple Ave, Austin, TX",
    time: "3:30 PM",
    duration: "3 hours",
    status: "scheduled",
  },
];

export function SchedulePanel() {
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [showBookingForm, setShowBookingForm] = useState(false);

  const formatDate = (d: Date) =>
    d.toLocaleDateString("en-US", {
      weekday: "long",
      year: "numeric",
      month: "long",
      day: "numeric",
    });

  const navigateDate = (offset: number) => {
    setSelectedDate((prev) => {
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
          <button
            onClick={() => navigateDate(-1)}
            className="p-2 hover:bg-slate-100 rounded-lg"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            onClick={() => setSelectedDate(new Date())}
            className="px-3 py-1.5 text-sm bg-slate-100 hover:bg-slate-200 rounded-lg"
          >
            Today
          </button>
          <button
            onClick={() => navigateDate(1)}
            className="p-2 hover:bg-slate-100 rounded-lg"
          >
            <ChevronRight size={20} />
          </button>
          <button
            onClick={() => setShowBookingForm(!showBookingForm)}
            className="ml-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700"
          >
            + Book Job
          </button>
        </div>
      </div>

      {/* Timeline */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-3">
          {mockJobs.map((job) => (
            <div
              key={job.id}
              className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md transition-shadow"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span
                      className={`px-2 py-0.5 text-xs font-medium rounded-full ${
                        job.status === "completed"
                          ? "bg-green-100 text-green-700"
                          : job.status === "in_progress"
                            ? "bg-yellow-100 text-yellow-700"
                            : "bg-blue-100 text-blue-700"
                      }`}
                    >
                      {job.status.replace("_", " ")}
                    </span>
                  </div>
                  <h3 className="font-semibold text-slate-900">{job.title}</h3>
                  <div className="mt-2 space-y-1 text-sm text-slate-600">
                    <div className="flex items-center gap-2">
                      <User size={14} />
                      {job.client}
                    </div>
                    <div className="flex items-center gap-2">
                      <MapPin size={14} />
                      {job.address}
                    </div>
                    <div className="flex items-center gap-2">
                      <Clock size={14} />
                      {job.time} ({job.duration})
                    </div>
                  </div>
                </div>
                <button className="text-sm text-blue-600 hover:underline">
                  Details
                </button>
              </div>
            </div>
          ))}
        </div>

        {mockJobs.length === 0 && (
          <div className="text-center py-12">
            <Calendar size={48} className="mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500">No jobs scheduled for this day</p>
          </div>
        )}
      </div>

      {/* Quick Stats */}
      <div className="p-4 border-t border-slate-200 bg-white">
        <div className="flex gap-6 text-sm">
          <div>
            <span className="text-slate-500">Total Jobs:</span>{" "}
            <span className="font-semibold">{mockJobs.length}</span>
          </div>
          <div>
            <span className="text-slate-500">Scheduled:</span>{" "}
            <span className="font-semibold text-blue-600">
              {mockJobs.filter((j) => j.status === "scheduled").length}
            </span>
          </div>
          <div>
            <span className="text-slate-500">In Progress:</span>{" "}
            <span className="font-semibold text-yellow-600">
              {mockJobs.filter((j) => j.status === "in_progress").length}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
