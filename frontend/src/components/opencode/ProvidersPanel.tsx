"use client";

import { useState, useEffect, useCallback } from "react";
import { Key, CheckCircle, Circle, ExternalLink, Trash2, Plus, Eye, EyeOff, Loader } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";

interface Provider {
  id: string;
  name: string;
  env: string;
  url: string;
  connected: boolean;
}

interface ProvidersPanelProps {
  authToken: string | null;
}

async function parseError(res: Response, fallback: string): Promise<string> {
  try {
    const body = await res.json() as { detail?: string };
    return body.detail || fallback;
  } catch {
    try {
      const text = await res.text();
      if (text && text.length < 200) return text;
    } catch { /* ignore */ }
    return `${fallback} (${res.status})`;
  }
}

export function ProvidersPanel({ authToken }: ProvidersPanelProps) {
  const [providers, setProviders] = useState<Provider[]>([]);
  const [loading, setLoading] = useState(true);
  const [addingFor, setAddingFor] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const fetchProviders = useCallback(async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_URL}/api/opencode/providers`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json() as { providers: Provider[] };
        setProviders(data.providers);
      } else {
        setError(await parseError(res, "Failed to load providers"));
      }
    } catch {
      setError("Could not reach the server — check your connection");
    } finally {
      setLoading(false);
    }
  }, [authToken]);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleSave = async (providerId: string) => {
    if (!apiKey.trim() || !authToken) return;
    setSaving(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/opencode/providers/keys`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${authToken}`,
        },
        body: JSON.stringify({ provider: providerId, api_key: apiKey.trim() }),
      });
      if (res.ok) {
        setSuccess(`${providers.find(p => p.id === providerId)?.name} connected successfully`);
        setAddingFor(null);
        setApiKey("");
        await fetchProviders();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(await parseError(res, "Failed to save key"));
      }
    } catch {
      setError("Could not reach the server — please check your connection and try again");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (providerId: string, providerName: string) => {
    if (!authToken) return;
    setDeleting(providerId);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/api/opencode/providers/${providerId}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        setSuccess(`${providerName} disconnected`);
        await fetchProviders();
        setTimeout(() => setSuccess(null), 3000);
      } else {
        setError(await parseError(res, "Failed to remove key"));
      }
    } catch {
      setError("Could not reach the server — please try again");
    } finally {
      setDeleting(null);
    }
  };

  const connected = providers.filter(p => p.connected);
  const available = providers.filter(p => !p.connected);

  return (
    <div className="flex-1 overflow-y-auto bg-[#0d1117] text-[#c9d1d9] p-6">
      <div className="max-w-2xl mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <div className="p-2 bg-[#1c2128] rounded-lg">
            <Key size={20} className="text-[#58a6ff]" />
          </div>
          <div>
            <h1 className="text-xl font-semibold text-white">AI Providers</h1>
            <p className="text-sm text-[#8b949e]">Connect your own API keys — OpenCode uses them directly</p>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-[#3d1f1f] border border-[#f85149] rounded-lg text-[#f85149] text-sm">
            {error}
          </div>
        )}
        {success && (
          <div className="mt-4 p-3 bg-[#1a3a2a] border border-[#3fb950] rounded-lg text-[#3fb950] text-sm">
            ✓ {success}
          </div>
        )}

        {loading ? (
          <div className="flex items-center justify-center py-16">
            <Loader size={24} className="animate-spin text-[#8b949e]" />
          </div>
        ) : (
          <>
            {connected.length > 0 && (
              <div className="mt-6">
                <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8b949e] mb-3">
                  Connected ({connected.length})
                </h2>
                <div className="space-y-2">
                  {connected.map(provider => (
                    <div
                      key={provider.id}
                      className="flex items-center justify-between p-4 bg-[#161b22] border border-[#238636] rounded-lg"
                    >
                      <div className="flex items-center gap-3">
                        <CheckCircle size={18} className="text-[#3fb950]" />
                        <div>
                          <p className="text-sm font-medium text-white">{provider.name}</p>
                          <p className="text-xs text-[#8b949e]">{provider.env}</p>
                        </div>
                      </div>
                      <button
                        onClick={() => handleDelete(provider.id, provider.name)}
                        disabled={deleting === provider.id}
                        className="p-1.5 text-[#8b949e] hover:text-[#f85149] rounded transition-colors disabled:opacity-50"
                        title="Disconnect"
                      >
                        {deleting === provider.id
                          ? <Loader size={16} className="animate-spin" />
                          : <Trash2 size={16} />}
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="mt-6">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-[#8b949e] mb-3">
                Available providers
              </h2>
              <div className="space-y-2">
                {available.map(provider => (
                  <div key={provider.id} className="bg-[#161b22] border border-[#30363d] rounded-lg overflow-hidden">
                    <div className="flex items-center justify-between p-4">
                      <div className="flex items-center gap-3">
                        <Circle size={18} className="text-[#484f58]" />
                        <div>
                          <p className="text-sm font-medium text-white">{provider.name}</p>
                          <p className="text-xs text-[#8b949e]">{provider.env}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <a
                          href={provider.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="p-1.5 text-[#8b949e] hover:text-[#58a6ff] rounded transition-colors"
                          title="Get API key"
                        >
                          <ExternalLink size={15} />
                        </a>
                        <button
                          onClick={() => {
                            setAddingFor(addingFor === provider.id ? null : provider.id);
                            setApiKey("");
                            setError(null);
                          }}
                          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#21262d] hover:bg-[#30363d] border border-[#30363d] text-[#c9d1d9] text-xs rounded-md transition-colors"
                        >
                          <Plus size={13} />
                          Connect
                        </button>
                      </div>
                    </div>

                    {addingFor === provider.id && (
                      <div className="px-4 pb-4 border-t border-[#30363d] pt-3">
                        <p className="text-xs text-[#8b949e] mb-2">
                          Paste your API key below. It&apos;s encrypted before storage and never logged.
                        </p>
                        <div className="flex gap-2">
                          <div className="relative flex-1">
                            <input
                              type={showKey ? "text" : "password"}
                              value={apiKey}
                              onChange={e => setApiKey(e.target.value)}
                              placeholder={`${provider.env}...`}
                              autoFocus
                              onKeyDown={e => e.key === "Enter" && handleSave(provider.id)}
                              className="w-full px-3 py-2 pr-9 bg-[#0d1117] border border-[#30363d] rounded-md text-sm text-white placeholder-[#484f58] focus:outline-none focus:border-[#58a6ff]"
                            />
                            <button
                              type="button"
                              onClick={() => setShowKey(v => !v)}
                              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[#8b949e] hover:text-white"
                            >
                              {showKey ? <EyeOff size={14} /> : <Eye size={14} />}
                            </button>
                          </div>
                          <button
                            onClick={() => handleSave(provider.id)}
                            disabled={saving || !apiKey.trim()}
                            className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm rounded-md disabled:opacity-50 transition-colors flex items-center gap-1.5"
                          >
                            {saving ? <Loader size={14} className="animate-spin" /> : null}
                            Save
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            <div className="mt-6 p-4 bg-[#161b22] border border-[#30363d] rounded-lg">
              <p className="text-xs text-[#8b949e] leading-relaxed">
                <span className="text-[#58a6ff] font-medium">How it works: </span>
                Your API keys are encrypted with Fernet (AES-128) and injected directly into your personal
                OpenCode server instance as environment variables. They&apos;re never sent to third parties or
                logged. Each user gets an isolated OpenCode process — your keys only run inside yours.
              </p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
