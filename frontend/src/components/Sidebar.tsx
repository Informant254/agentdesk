"use client";

import { useEffect, useState, type ReactNode } from "react";
import { MessageSquare, Calendar, FileText, Terminal, User, Key, Map } from "lucide-react";
import { supabase } from "@/lib/supabase";
import type { User as SupabaseUser } from "@supabase/supabase-js";

type Panel = "chat" | "schedule" | "invoices" | "opencode" | "providers" | "profile" | "route-map";

interface SidebarProps {
  activePanel: Panel;
  onNavigate: (panel: Panel) => void;
}

const navItems: { id: Panel; label: string; icon: ReactNode; badge?: string }[] = [
  { id: "chat",      label: "AI Assistant",      icon: <MessageSquare size={20} /> },
  { id: "opencode",  label: "OpenCode Terminal",  icon: <Terminal size={20} />, badge: "NEW" },
  { id: "providers", label: "AI Providers",       icon: <Key size={20} /> },
  { id: "schedule",  label: "Schedule",           icon: <Calendar size={20} /> },
  { id: "route-map", label: "Route Map",           icon: <Map size={20} /> },
  { id: "invoices",  label: "Invoices",           icon: <FileText size={20} /> },
];

export function Sidebar({ activePanel, onNavigate }: SidebarProps) {
  const [user, setUser] = useState<SupabaseUser | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => setUser(session?.user ?? null));
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) =>
      setUser(session?.user ?? null)
    );
    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    localStorage.removeItem("agentdesk_token");
    window.location.reload();
  };

  const avatarUrl = user?.user_metadata?.avatar_url;
  const name = user?.user_metadata?.full_name
    ?? user?.user_metadata?.name
    ?? user?.email?.split("@")[0]
    ?? "User";
  const initials = name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2);

  return (
    <aside className="w-64 bg-slate-900 text-white flex flex-col">
      {/* Logo */}
      <div className="p-6 border-b border-slate-700">
        <h1 className="text-xl font-bold tracking-tight">AgentDesk</h1>
        <p className="text-slate-400 text-sm mt-1">Trades AI Assistant</p>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1">
        {navItems.map(item => (
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

      {/* User profile */}
      <div className="p-4 border-t border-slate-700 space-y-1">
        <button
          onClick={() => onNavigate("profile")}
          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
            activePanel === "profile" ? "bg-blue-600 text-white" : "text-slate-300 hover:bg-slate-800"
          }`}
        >
          {avatarUrl ? (
            <img src={avatarUrl} alt={name} className="w-7 h-7 rounded-full object-cover" />
          ) : (
            <div className="w-7 h-7 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold">
              {initials}
            </div>
          )}
          <span className="flex-1 text-left font-medium truncate">{name}</span>
          <User size={16} className="flex-shrink-0 opacity-60" />
        </button>
        <button
          onClick={handleSignOut}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-slate-400 hover:bg-slate-800 hover:text-white transition-colors"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
