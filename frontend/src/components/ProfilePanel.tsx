"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

const PROVIDER_LABELS: Record<string, { label: string; color: string }> = {
  github:  { label: "GitHub",    color: "bg-gray-900 text-white" },
  google:  { label: "Google",    color: "bg-blue-500 text-white" },
  gitlab:  { label: "GitLab",    color: "bg-orange-500 text-white" },
  azure:   { label: "Microsoft", color: "bg-blue-700 text-white" },
  apple:   { label: "Apple",     color: "bg-black text-white" },
  email:   { label: "Email",     color: "bg-slate-500 text-white" },
};

export function ProfilePanel() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [signingOut, setSigningOut] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null);
      setLoading(false);
    });
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_e, session) => {
      setUser(session?.user ?? null);
    });
    return () => subscription.unsubscribe();
  }, []);

  const handleSignOut = async () => {
    setSigningOut(true);
    await supabase.auth.signOut();
    localStorage.removeItem("agentdesk_token");
    window.location.reload();
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex-1 flex items-center justify-center text-slate-500">
        No profile found.
      </div>
    );
  }

  const provider = user.app_metadata?.provider ?? "email";
  const providerMeta = PROVIDER_LABELS[provider] ?? { label: provider, color: "bg-slate-500 text-white" };
  const avatarUrl = user.user_metadata?.avatar_url;
  const name = user.user_metadata?.full_name ?? user.user_metadata?.name ?? user.email?.split("@")[0] ?? "User";
  const email = user.email ?? "";
  const createdAt = new Date(user.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" });
  const initials = name.split(" ").map((n: string) => n[0]).join("").toUpperCase().slice(0, 2);

  return (
    <div className="flex-1 p-8 overflow-y-auto">
      <h2 className="text-2xl font-bold text-slate-900 mb-8">Your Profile</h2>

      {/* Avatar + name card */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-6 flex items-center gap-6">
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt={name}
            className="w-20 h-20 rounded-full object-cover ring-4 ring-blue-100"
          />
        ) : (
          <div className="w-20 h-20 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold ring-4 ring-blue-100">
            {initials}
          </div>
        )}
        <div>
          <h3 className="text-xl font-semibold text-slate-900">{name}</h3>
          <p className="text-slate-500 mt-0.5">{email}</p>
          <span className={`inline-block mt-2 px-3 py-1 text-xs font-semibold rounded-full ${providerMeta.color}`}>
            Signed in with {providerMeta.label}
          </span>
        </div>
      </div>

      {/* Account details */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-200 divide-y divide-slate-100 mb-6">
        <div className="px-6 py-4 flex justify-between items-center">
          <span className="text-sm font-medium text-slate-500">User ID</span>
          <span className="text-sm text-slate-700 font-mono">{user.id.slice(0, 16)}…</span>
        </div>
        <div className="px-6 py-4 flex justify-between items-center">
          <span className="text-sm font-medium text-slate-500">Email</span>
          <span className="text-sm text-slate-700">{email}</span>
        </div>
        <div className="px-6 py-4 flex justify-between items-center">
          <span className="text-sm font-medium text-slate-500">Sign-in method</span>
          <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full ${providerMeta.color}`}>
            {providerMeta.label}
          </span>
        </div>
        <div className="px-6 py-4 flex justify-between items-center">
          <span className="text-sm font-medium text-slate-500">Member since</span>
          <span className="text-sm text-slate-700">{createdAt}</span>
        </div>
      </div>

      {/* Sign out */}
      <div className="bg-white rounded-2xl shadow-sm border border-red-100 p-6">
        <h4 className="text-sm font-semibold text-slate-800 mb-1">Sign out</h4>
        <p className="text-sm text-slate-500 mb-4">You will be returned to the login screen.</p>
        <button
          onClick={handleSignOut}
          disabled={signingOut}
          className="px-5 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700 disabled:opacity-50 transition-colors"
        >
          {signingOut ? "Signing out…" : "Sign Out"}
        </button>
      </div>
    </div>
  );
}
