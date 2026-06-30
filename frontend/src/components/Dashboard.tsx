"use client";

import { useState, useEffect } from "react";
import { Sidebar } from "./Sidebar";
import { ChatPanel } from "./ChatPanel";
import { SchedulePanel } from "./SchedulePanel";
import { InvoicesPanel } from "./InvoicesPanel";
import { OpenCodePanel } from "./opencode";
import { supabase } from "@/lib/supabase";
import { setAuthToken } from "@/lib/api";

type Panel = "chat" | "schedule" | "invoices" | "opencode";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://agentdesk-v2.netlify.app";

export function Dashboard() {
  const [activePanel, setActivePanel] = useState<Panel>("chat");
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);

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
          }
        } catch {}
        setIsAuthenticated(true);
      } else {
        setIsAuthenticated(false);
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
    <div className="flex h-screen">
      <Sidebar activePanel={activePanel} onNavigate={setActivePanel} />
      <main className="flex-1 overflow-hidden">
        {activePanel === "chat" && <ChatPanel />}
        {activePanel === "opencode" && <OpenCodePanel />}
        {activePanel === "schedule" && <SchedulePanel />}
        {activePanel === "invoices" && <InvoicesPanel />}
      </main>
    </div>
  );
}

const PROVIDERS = [
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
  {
    id: "github" as const,
    name: "GitHub",
    cls: "bg-gray-900 hover:bg-gray-800 text-white",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor" aria-hidden="true">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
      </svg>
    ),
  },
  {
    id: "gitlab" as const,
    name: "GitLab",
    cls: "bg-orange-600 hover:bg-orange-700 text-white",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor" aria-hidden="true">
        <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.49h8.1l2.44-7.51A.42.42 0 0 1 18.6 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51L23 13.45a.84.84 0 0 1-.35.94z"/>
      </svg>
    ),
  },
  {
    id: "azure" as const,
    name: "Microsoft",
    cls: "bg-blue-700 hover:bg-blue-800 text-white",
    icon: (
      <svg viewBox="0 0 23 23" className="w-5 h-5" fill="currentColor" aria-hidden="true">
        <path d="M11 11H0V0h11v11zm12 0H12V0h11v11zM11 23H0V12h11v11zm12 0H12V12h11v11z"/>
      </svg>
    ),
  },
  {
    id: "apple" as const,
    name: "Apple",
    cls: "bg-black hover:bg-gray-900 text-white",
    icon: (
      <svg viewBox="0 0 24 24" className="w-5 h-5" fill="currentColor" aria-hidden="true">
        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/>
      </svg>
    ),
  },
] as const;

type ProviderId = typeof PROVIDERS[number]["id"];

function AuthScreen({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [businessName, setBusinessName] = useState("");
  const [businessType, setBusinessType] = useState("hvac");
  const [isRegistering, setIsRegistering] = useState(false);
  const [loading, setLoading] = useState(false);
  const [oauthLoading, setOauthLoading] = useState<ProviderId | null>(null);
  const [error, setError] = useState("");

  const handleOAuthSignIn = async (provider: ProviderId) => {
    setOauthLoading(provider);
    setError("");
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider,
        options: { redirectTo: `${APP_URL}/auth/callback` },
      });
      if (error) { setError(error.message); setOauthLoading(null); }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "OAuth sign in failed");
      setOauthLoading(null);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const { login: apiLogin, register: apiRegister } = await import("@/lib/api");
      if (isRegistering) {
        await apiRegister(email, password, businessName, businessType);
      } else {
        await apiLogin(email, password);
      }
      onLogin();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-slate-100">
      <div className="w-full max-w-md p-8 bg-white rounded-2xl shadow-xl">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900">AgentDesk</h1>
          <p className="text-slate-500 mt-2">AI Assistant for Trades Businesses</p>
        </div>

        <div className="space-y-3 mb-6">
          {PROVIDERS.map((provider) => (
            <button
              key={provider.id}
              onClick={() => handleOAuthSignIn(provider.id)}
              disabled={oauthLoading !== null}
              className={`w-full flex items-center justify-center gap-3 py-2.5 px-4 rounded-lg font-medium transition-colors disabled:opacity-50 ${provider.cls}`}
            >
              {oauthLoading === provider.id ? (
                <div className="w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : provider.icon}
              Continue with {provider.name}
            </button>
          ))}
        </div>

        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-slate-200" />
          </div>
          <div className="relative flex justify-center text-sm">
            <span className="px-3 bg-white text-slate-400">or continue with email</span>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isRegistering && (
            <>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Name</label>
                <input type="text" value={businessName} onChange={(e) => setBusinessName(e.target.value)}
                  className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="Smith HVAC Services" required />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Business Type</label>
                <select value={businessType} onChange={(e) => setBusinessType(e.target.value)}
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
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="you@business.com" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Password</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
              className="w-full px-4 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="••••••••" required />
          </div>
          {error && <p className="text-red-500 text-sm">{error}</p>}
          <button type="submit" disabled={loading}
            className="w-full py-2 px-4 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {loading ? "Please wait..." : isRegistering ? "Create Account" : "Sign In"}
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
