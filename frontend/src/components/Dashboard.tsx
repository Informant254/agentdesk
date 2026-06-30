"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { ChatPanel } from "./ChatPanel";
import { SchedulePanel } from "./SchedulePanel";
import { InvoicesPanel } from "./InvoicesPanel";
import { OpenCodePanel, ProvidersPanel } from "./opencode";
import { ProfilePanel } from "./ProfilePanel";
import { supabase } from "@/lib/supabase";
import { setAuthToken } from "@/lib/api";

type Panel = "chat" | "schedule" | "invoices" | "opencode" | "providers" | "profile";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";

export function Dashboard() {
  const [activePanel,     setActivePanel]     = useState<Panel>("chat");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth,    setCheckingAuth]    = useState(true);
  const [authToken,       setAuthTokenState]  = useState<string | null>(null);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      if (session) {
        try {
          const res = await fetch(`${API_URL}/api/auth/social`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ supabase_token: session.access_token }),
          });
          if (res.ok) {
            const data = await res.json();
            setAuthToken(data.access_token);
            setAuthTokenState(data.access_token);
          }
        } catch {}
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
        setAuthTokenState(null);
      }
      setCheckingAuth(false);
    });
    return () => subscription.unsubscribe();
  }, []);

  if (checkingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <AuthScreen onLogin={() => setIsAuthenticated(true)} />;
  }

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar activePanel={activePanel} onNavigate={setActivePanel} />
      <main className="flex-1 overflow-hidden flex">
        {activePanel === "chat"      && <ChatPanel />}
        {activePanel === "opencode"  && (
          <OpenCodePanel
            authToken={authToken}
            onOpenProviders={() => setActivePanel("providers")}
          />
        )}
        {activePanel === "providers" && <ProvidersPanel authToken={authToken} />}
        {activePanel === "schedule"  && <SchedulePanel />}
        {activePanel === "invoices"  && <InvoicesPanel />}
        {activePanel === "profile"   && <ProfilePanel />}
      </main>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Auth screen (unchanged from original)
// ─────────────────────────────────────────────────────────────────────────────

const PROVIDERS_AUTH = [
  {
    id: "google" as const,
    name: "Google",
    cls: "bg-white hover:bg-gray-50 border border-gray-300 text-gray-700",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" aria-hidden="true">
        <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
        <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
        <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
        <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
      </svg>
    ),
  },
];

function AuthScreen({ onLogin }: { onLogin: () => void }) {
  const [isRegistering, setIsRegistering] = useState(false);
  const [email,         setEmail]         = useState("");
  const [password,      setPassword]      = useState("");
  const [businessName,  setBusinessName]  = useState("");
  const [businessType,  setBusinessType]  = useState("hvac");
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState("");

  const handleOAuth = async (provider: "google") => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider,
      options: { redirectTo: `${window.location.origin}/auth/callback` },
    });
    if (error) setError(error.message);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const body = isRegistering
        ? { email, password, business_name: businessName, business_type: businessType }
        : { email, password };
      const endpoint = isRegistering ? "/api/auth/register" : "/api/auth/login";
      const res = await fetch(`${API_URL}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || "Authentication failed");
        return;
      }
      const data = await res.json();
      setAuthToken(data.access_token);
      onLogin();
    } catch {
      setError("Network error — please try again");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100 p-4">
      <div className="bg-white rounded-2xl shadow-xl p-8 w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">AgentDesk</h1>
          <p className="text-slate-500 mt-2">AI Assistant for Trades Businesses</p>
        </div>

        {/* OAuth */}
        <div className="space-y-3 mb-6">
          {PROVIDERS_AUTH.map(provider => (
            <button
              key={provider.id}
              onClick={() => handleOAuth(provider.id)}
              className={`w-full flex items-center justify-center gap-3 px-4 py-3 rounded-xl font-medium transition-colors ${provider.cls}`}
            >
              {provider.icon}
              Continue with {provider.name}
            </button>
          ))}
        </div>

        <div className="relative mb-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="bg-white px-4 text-slate-400">or continue with email</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegistering && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Name</label>
                <input type="text" value={businessName} onChange={e => setBusinessName(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Smith HVAC Services" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Type</label>
                <select value={businessType} onChange={e => setBusinessType(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500">
                  <option value="hvac">HVAC</option>
                  <option value="plumbing">Plumbing</option>
                  <option value="electrical">Electrical</option>
                  <option value="general">General Contractor</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </>
          )}
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="you@business.com" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••" required />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? "Please wait…" : isRegistering ? "Create Account" : "Sign In"}
          </button>
        </form>

        <p className="text-center mt-6 text-sm text-slate-500">
          {isRegistering ? "Already have an account?" : "Don't have an account?"}{" "}
          <button onClick={() => setIsRegistering(!isRegistering)} className="text-blue-600 font-medium hover:underline">
            {isRegistering ? "Sign In" : "Sign Up"}
          </button>
        </p>
      </div>
    </div>
  );
}
