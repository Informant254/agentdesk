"use client";

import { useState } from "react";
import { FileText, DollarSign, AlertCircle, CheckCircle, Clock } from "lucide-react";

interface Invoice {
  id: string;
  client: string;
  amount: number;
  status: "draft" | "sent" | "paid" | "overdue";
  dueDate: string;
  jobTitle: string;
}

const mockInvoices: Invoice[] = [
  {
    id: "INV-001",
    client: "Johnson Residence",
    amount: 85000,
    status: "paid",
    dueDate: "2026-06-15",
    jobTitle: "AC Unit Repair",
  },
  {
    id: "INV-002",
    client: "Smith Commercial",
    amount: 27500,
    status: "overdue",
    dueDate: "2026-06-20",
    jobTitle: "Furnace Inspection",
  },
  {
    id: "INV-003",
    client: "Williams Home",
    amount: 142500,
    status: "sent",
    dueDate: "2026-07-15",
    jobTitle: "Emergency Pipe Burst",
  },
  {
    id: "INV-004",
    client: "Davis Office",
    amount: 52000,
    status: "draft",
    dueDate: "2026-07-30",
    jobTitle: "HVAC Maintenance",
  },
];

function formatCents(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

const statusConfig = {
  draft: { icon: Clock, color: "text-slate-500", bg: "bg-slate-100" },
  sent: { icon: FileText, color: "text-blue-600", bg: "bg-blue-100" },
  paid: { icon: CheckCircle, color: "text-green-600", bg: "bg-green-100" },
  overdue: { icon: AlertCircle, color: "text-red-600", bg: "bg-red-100" },
};

export function InvoicesPanel() {
  const [filter, setFilter] = useState<string>("all");

  const filtered =
    filter === "all"
      ? mockInvoices
      : mockInvoices.filter((inv) => inv.status === filter);

  const totalOutstanding = mockInvoices
    .filter((inv) => inv.status !== "paid")
    .reduce((sum, inv) => sum + inv.amount, 0);

  const totalOverdue = mockInvoices
    .filter((inv) => inv.status === "overdue")
    .reduce((sum, inv) => sum + inv.amount, 0);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white">
        <h2 className="text-lg font-semibold text-slate-900">Invoices</h2>
        <p className="text-sm text-slate-500">Track and manage your invoices</p>
      </div>

      {/* Stats */}
      <div className="p-4 bg-white border-b border-slate-200">
        <div className="grid grid-cols-3 gap-4">
          <div className="bg-slate-50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
              <DollarSign size={16} />
              Outstanding
            </div>
            <p className="text-2xl font-bold text-slate-900">
              {formatCents(totalOutstanding)}
            </p>
          </div>
          <div className="bg-red-50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-red-500 text-sm mb-1">
              <AlertCircle size={16} />
              Overdue
            </div>
            <p className="text-2xl font-bold text-red-600">
              {formatCents(totalOverdue)}
            </p>
          </div>
          <div className="bg-green-50 rounded-xl p-4">
            <div className="flex items-center gap-2 text-green-500 text-sm mb-1">
              <CheckCircle size={16} />
              Paid This Month
            </div>
            <p className="text-2xl font-bold text-green-600">
              {formatCents(
                mockInvoices
                  .filter((inv) => inv.status === "paid")
                  .reduce((sum, inv) => sum + inv.amount, 0)
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Filter */}
      <div className="p-4 bg-white border-b border-slate-200">
        <div className="flex gap-2">
          {["all", "draft", "sent", "paid", "overdue"].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1.5 text-sm rounded-lg capitalize ${
                filter === s
                  ? "bg-blue-600 text-white"
                  : "bg-slate-100 text-slate-600 hover:bg-slate-200"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Invoice List */}
      <div className="flex-1 overflow-y-auto p-4">
        <div className="space-y-2">
          {filtered.map((inv) => {
            const statusInfo = statusConfig[inv.status];
            const StatusIcon = statusInfo.icon;
            return (
              <div
                key={inv.id}
                className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div
                      className={`w-10 h-10 rounded-lg ${statusInfo.bg} flex items-center justify-center`}
                    >
                      <StatusIcon size={20} className={statusInfo.color} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-sm text-slate-500">
                          {inv.id}
                        </span>
                        <span
                          className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${statusInfo.bg} ${statusInfo.color}`}
                        >
                          {inv.status}
                        </span>
                      </div>
                      <p className="font-medium text-slate-900">
                        {inv.jobTitle}
                      </p>
                      <p className="text-sm text-slate-500">{inv.client}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-slate-900">
                      {formatCents(inv.amount)}
                    </p>
                    <p className="text-sm text-slate-500">
                      Due: {new Date(inv.dueDate).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
