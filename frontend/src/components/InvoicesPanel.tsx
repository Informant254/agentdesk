"use client";

import { useState, useEffect, useCallback } from "react";
import {
  FileText, DollarSign, AlertCircle, CheckCircle,
  Clock, Loader2, Plus, RefreshCw,
} from "lucide-react";
import { getInvoiceList, createInvoiceDirect, type Invoice } from "@/lib/api";

function formatCents(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

function formatDate(str: string) {
  return new Date(str + "T00:00:00").toLocaleDateString("en-US", {
    month: "short", day: "numeric", year: "numeric",
  });
}

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; bg: string; label: string }> = {
  draft:   { icon: Clock,          color: "text-slate-500",  bg: "bg-slate-100",  label: "Draft" },
  sent:    { icon: FileText,       color: "text-blue-600",   bg: "bg-blue-100",   label: "Sent" },
  paid:    { icon: CheckCircle,    color: "text-green-600",  bg: "bg-green-100",  label: "Paid" },
  overdue: { icon: AlertCircle,    color: "text-red-600",    bg: "bg-red-100",    label: "Overdue" },
};

interface NewInvoiceForm {
  client_name: string;
  job_title: string;
  amount: string;   // dollars (user types "$850")
  status: string;
  due_date: string;
  notes: string;
}

export function InvoicesPanel() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [summary, setSummary] = useState({ outstanding_cents: 0, overdue_cents: 0, paid_this_month_cents: 0, total: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [showForm, setShowForm] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState<NewInvoiceForm>({
    client_name: "", job_title: "", amount: "", status: "draft", due_date: "", notes: "",
  });

  const fetchInvoices = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await getInvoiceList();
      setInvoices(res.invoices ?? []);
      setSummary(res.summary ?? { outstanding_cents: 0, overdue_cents: 0, paid_this_month_cents: 0, total: 0 });
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchInvoices(); }, [fetchInvoices]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const amount_cents = Math.round(parseFloat(form.amount) * 100);
      if (isNaN(amount_cents) || amount_cents <= 0) throw new Error("Enter a valid amount");
      await createInvoiceDirect({
        client_name: form.client_name,
        job_title: form.job_title,
        amount_cents,
        status: form.status,
        due_date: form.due_date,
        notes: form.notes,
      });
      setShowForm(false);
      setForm({ client_name: "", job_title: "", amount: "", status: "draft", due_date: "", notes: "" });
      await fetchInvoices();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create invoice");
    } finally {
      setSubmitting(false);
    }
  };

  const filtered = filter === "all" ? invoices : invoices.filter(i => i.status === filter);

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b border-slate-200 bg-white flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Invoices</h2>
          <p className="text-sm text-slate-500">Track and manage your invoices</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchInvoices} disabled={loading} className="p-2 hover:bg-slate-100 rounded-lg text-slate-400 disabled:opacity-40" title="Refresh">
            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
          </button>
          <button onClick={() => setShowForm(v => !v)}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 flex items-center gap-1.5">
            <Plus size={16} />
            New Invoice
          </button>
        </div>
      </div>

      {/* New Invoice Form */}
      {showForm && (
        <div className="p-4 bg-blue-50 border-b border-blue-200">
          <h3 className="font-semibold text-slate-800 mb-3">Create Invoice</h3>
          <form onSubmit={handleCreate} className="grid grid-cols-2 gap-3">
            <input required className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="Client name" value={form.client_name} onChange={e => setForm(f => ({ ...f, client_name: e.target.value }))} />
            <input required className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="Job / service title" value={form.job_title} onChange={e => setForm(f => ({ ...f, job_title: e.target.value }))} />
            <input required type="number" min="0.01" step="0.01" className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              placeholder="Amount (e.g. 850.00)" value={form.amount} onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} />
            <select className="px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
              value={form.status} onChange={e => setForm(f => ({ ...f, status: e.target.value }))}>
              <option value="draft">Draft</option>
              <option value="sent">Sent</option>
              <option value="paid">Paid</option>
              <option value="overdue">Overdue</option>
            </select>
            <div>
              <label className="block text-xs text-slate-500 mb-1">Due date</label>
              <input required type="date" className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
                value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} />
            </div>
            <div className="flex items-end gap-2">
              <button type="submit" disabled={submitting}
                className="flex-1 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50">
                {submitting ? "Saving…" : "Create"}
              </button>
              <button type="button" onClick={() => setShowForm(false)}
                className="px-3 py-2 bg-slate-200 text-slate-700 text-sm rounded-lg hover:bg-slate-300">
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Stats */}
      {!loading && (
        <div className="p-4 bg-white border-b border-slate-200">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-slate-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-slate-500 text-sm mb-1">
                <DollarSign size={16} />
                Outstanding
              </div>
              <p className="text-2xl font-bold text-slate-900">{formatCents(summary.outstanding_cents)}</p>
            </div>
            <div className="bg-red-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-red-500 text-sm mb-1">
                <AlertCircle size={16} />
                Overdue
              </div>
              <p className="text-2xl font-bold text-red-600">{formatCents(summary.overdue_cents)}</p>
            </div>
            <div className="bg-green-50 rounded-xl p-4">
              <div className="flex items-center gap-2 text-green-500 text-sm mb-1">
                <CheckCircle size={16} />
                Paid This Month
              </div>
              <p className="text-2xl font-bold text-green-600">{formatCents(summary.paid_this_month_cents)}</p>
            </div>
          </div>
        </div>
      )}

      {/* Filter */}
      <div className="px-4 py-3 bg-white border-b border-slate-200">
        <div className="flex gap-2">
          {["all", "draft", "sent", "paid", "overdue"].map(s => (
            <button key={s} onClick={() => setFilter(s)}
              className={`px-3 py-1.5 text-sm rounded-lg capitalize ${filter === s ? "bg-blue-600 text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200"}`}>
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* List */}
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
              <p className="font-medium">Failed to load invoices</p>
              <p className="text-xs mt-0.5">{error}</p>
              <button onClick={fetchInvoices} className="mt-2 text-xs underline hover:no-underline">Retry</button>
            </div>
          </div>
        )}

        {!loading && !error && filtered.length === 0 && (
          <div className="text-center py-16">
            <FileText size={48} className="mx-auto text-slate-300 mb-4" />
            <p className="text-slate-500 font-medium">
              {filter === "all" ? "No invoices yet" : `No ${filter} invoices`}
            </p>
            {filter === "all" && <p className="text-sm text-slate-400 mt-1">Click "New Invoice" to create one.</p>}
          </div>
        )}

        {!loading && filtered.length > 0 && (
          <div className="space-y-2">
            {filtered.map(inv => {
              const cfg = STATUS_CONFIG[inv.status] ?? STATUS_CONFIG.draft;
              const StatusIcon = cfg.icon;
              return (
                <div key={inv.id} className="bg-white border border-slate-200 rounded-xl p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg ${cfg.bg} flex items-center justify-center`}>
                        <StatusIcon size={20} className={cfg.color} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-sm text-slate-500">
                            {inv.id.length > 12 ? inv.id.slice(0, 8).toUpperCase() : inv.id}
                          </span>
                          <span className={`px-2 py-0.5 text-xs font-medium rounded-full capitalize ${cfg.bg} ${cfg.color}`}>
                            {cfg.label}
                          </span>
                        </div>
                        <p className="font-medium text-slate-900">{inv.job_title}</p>
                        <p className="text-sm text-slate-500">{inv.client_name}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-bold text-slate-900">{formatCents(inv.amount_cents)}</p>
                      <p className="text-sm text-slate-500">Due: {formatDate(inv.due_date)}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
