"use client";

import {
  MessageSquare,
  Calendar,
  FileText,
  Terminal,
  Settings,
  LogOut,
} from "lucide-react";

type Panel = "chat" | "schedule" | "invoices" | "opencode";

interface SidebarProps {
  activePanel: Panel;
  onNavigate: (panel: Panel) => void;
}

const navItems: { id: Panel; label: string; icon: React.ReactNode; badge?: string }[] = [
  { id: "chat", label: "AI Assistant", icon: <MessageSquare size={20} /> },
  { id: "opencode", label: "OpenCode Terminal", icon: <Terminal size={20} />, badge: "NEW" },
  { id: "schedule", label: "Schedule", icon: <Calendar size={20} /> },
  { id: "invoices", label: "Invoices", icon: <FileText size={20} /> },
];

export function Sidebar({ activePanel, onNavigate }: SidebarProps) {
  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-tight">AgentDesk</h1>
        <p className="text-slate-400 text-sm mt-1">Trades AI Assistant</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => onNavigate(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
              activePanel === item.id
                ? "bg-blue-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            }`}
          >
            {item.icon}
            <span className="flex-1 text-left">{item.label}</span>
            {item.badge && (
              <span className="px-1.5 py-0.5 text-[10px] font-bold bg-green-500 text-white rounded">
                {item.badge}
              </span>
            )}
          </button>
        ))}
      </nav>

      {/* Bottom actions */}
      <div className="p-4 border-t border-slate-700 space-y-1">
        <button className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white">
          <Settings size={20} />
          Settings
        </button>
        <button
          onClick={() => {
            localStorage.removeItem("agentdesk_token");
            window.location.reload();
          }}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium text-slate-300 hover:bg-slate-800 hover:text-white"
        >
          <LogOut size={20} />
          Sign Out
        </button>
      </div>
    </aside>
  );
}
