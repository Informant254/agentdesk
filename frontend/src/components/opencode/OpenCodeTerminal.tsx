"use client";

import "@xterm/xterm/css/xterm.css";
import { useEffect, useRef, useState, useCallback } from "react";
import { Loader, RefreshCw, Wifi, WifiOff, Settings } from "lucide-react";

interface TerminalSession {
  id: string;
  title: string;
  created_at: string;
}

interface OpenCodeTerminalProps {
  sessionId: string;
  authToken: string | null;
  onOpenProviders?: () => void;
}

const API_HTTP = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";
const API_WS   = API_HTTP.replace(/^https:\/\//, "wss://").replace(/^http:\/\//, "ws://");

export function OpenCodeTerminal({ sessionId, authToken, onOpenProviders }: OpenCodeTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef     = useRef<{ dispose(): void; writeln(s: string): void; write(s: string): void; onKey(h: (e: { key: string; domEvent: KeyboardEvent }) => void): void } | null>(null);
  const wsRef       = useRef<WebSocket | null>(null);
  const fitRef      = useRef<{ fit(): void } | null>(null);

  const [isConnected,        setIsConnected]        = useState(false);
  const [isConnecting,       setIsConnecting]       = useState(false);
  const [connectedProviders, setConnectedProviders] = useState<string[]>([]);

  const connectTerminal = useCallback(async (sid: string) => {
    if (!terminalRef.current || !authToken) return;

    const { Terminal }      = await import("@xterm/xterm");
    const { FitAddon }      = await import("@xterm/addon-fit");
    const { WebLinksAddon } = await import("@xterm/addon-web-links");

    if (termRef.current) termRef.current.dispose();
    if (wsRef.current)   wsRef.current.close();

    setIsConnecting(true);

    const term = new Terminal({
      theme: {
        background: "#0d1117", foreground: "#c9d1d9", cursor: "#58a6ff",
        cursorAccent: "#0d1117", selectionBackground: "rgba(56,139,253,0.4)",
        black: "#0d1117",   red: "#ff7b72",     green: "#3fb950",
        yellow: "#d29922",  blue: "#58a6ff",    magenta: "#bc8cff",
        cyan: "#39c5cf",    white: "#c9d1d9",
        brightBlack: "#484f58",   brightRed: "#ffa198",
        brightGreen: "#56d364",   brightYellow: "#e3b341",
        brightBlue: "#79c0ff",    brightMagenta: "#d2a8ff",
        brightCyan: "#56d4dd",    brightWhite: "#f0f6fc",
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
      fontSize: 14, lineHeight: 1.4, cursorBlink: true, cursorStyle: "bar",
      scrollback: 10000, allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(new WebLinksAddon());
    term.open(terminalRef.current);
    setTimeout(() => fitAddon.fit(), 100);

    termRef.current = term;
    fitRef.current  = fitAddon;

    term.writeln("\x1b[1;34m  AgentDesk Terminal\x1b[0m");
    term.writeln("\x1b[90m  Powered by OpenCode — connecting…\x1b[0m");
    term.writeln("");

    const ws = new WebSocket(`${API_WS}/api/opencode/ws/${sid}`);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "auth", token: authToken }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string);

        if (msg.type === "connected") {
          setIsConnected(true);
          setIsConnecting(false);
          setConnectedProviders(msg.providers ?? []);
          term.writeln("\x1b[32m  ✓ Connected to OpenCode\x1b[0m");
          if ((msg.providers ?? []).length > 0) {
            term.writeln(`\x1b[90m  Active providers: ${(msg.providers as string[]).join(", ")}\x1b[0m`);
          } else {
            term.writeln("\x1b[33m  ⚠  No AI providers configured — click \"Add API keys\" above\x1b[0m");
          }
          term.writeln("");
          term.write("\x1b[1;36m❯\x1b[0m ");
          return;
        }

        if (msg.type === "message") {
          const data = msg.data as { parts?: { type: string; text: string }[] };
          if (data?.parts) {
            for (const part of data.parts) {
              if (part.type === "text") {
                for (const line of part.text.split("\n")) term.writeln(line);
              }
            }
          }
          term.writeln("");
          term.write("\x1b[1;36m❯\x1b[0m ");
          return;
        }

        if (msg.type === "error") {
          term.writeln(`\x1b[31m  ✗ ${msg.message as string}\x1b[0m`);
          term.write("\x1b[1;36m❯\x1b[0m ");
        }
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      setIsConnected(false);
      term.writeln("\n\x1b[33m  Connection closed\x1b[0m");
    };

    ws.onerror = () => {
      setIsConnected(false);
      setIsConnecting(false);
      term.writeln("\x1b[31m  ✗ Failed to connect to OpenCode server\x1b[0m");
      term.write("\x1b[1;36m❯\x1b[0m ");
    };

    // Input handling
    let inputBuffer = "";
    term.onKey(({ key, domEvent }) => {
      const code = domEvent.keyCode;
      if (code === 13) {
        const content = inputBuffer.trim();
        term.writeln("");
        inputBuffer = "";
        if (content && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "message", content }));
        } else {
          term.write("\x1b[1;36m❯\x1b[0m ");
        }
      } else if (code === 8) {
        if (inputBuffer.length > 0) {
          inputBuffer = inputBuffer.slice(0, -1);
          term.write("\b \b");
        }
      } else {
        inputBuffer += key;
        term.write(key);
      }
    });

    const ro = new ResizeObserver(() => { try { fitRef.current?.fit(); } catch { /* ignore */ } });
    if (terminalRef.current) ro.observe(terminalRef.current);

    return () => { ro.disconnect(); ws.close(); term.dispose(); };
  }, [authToken]);

  useEffect(() => {
    let cleanup: (() => void) | undefined;
    connectTerminal(sessionId).then(fn => { cleanup = fn; });
    return () => { cleanup?.(); };
  }, [sessionId, connectTerminal]);

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      <div className="flex items-center justify-between px-4 py-1.5 bg-[#161b22] border-b border-[#30363d] text-xs">
        <div className="flex items-center gap-2">
          {isConnecting ? (
            <><Loader size={12} className="animate-spin text-[#d29922]" /><span className="text-[#d29922]">Connecting…</span></>
          ) : isConnected ? (
            <><Wifi size={12} className="text-[#3fb950]" /><span className="text-[#3fb950]">Connected</span></>
          ) : (
            <><WifiOff size={12} className="text-[#f85149]" /><span className="text-[#f85149]">Disconnected</span></>
          )}
          {connectedProviders.length > 0 && (
            <span className="text-[#484f58]">· {connectedProviders.join(", ")}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {connectedProviders.length === 0 && onOpenProviders && (
            <button onClick={onOpenProviders}
              className="flex items-center gap-1 px-2 py-0.5 bg-[#d29922]/20 text-[#d29922] rounded hover:bg-[#d29922]/30 transition-colors">
              <Settings size={11} />Add API keys
            </button>
          )}
          <button onClick={() => connectTerminal(sessionId)}
            className="flex items-center gap-1 text-[#8b949e] hover:text-white transition-colors">
            <RefreshCw size={12} />Reconnect
          </button>
        </div>
      </div>
      <div ref={terminalRef} className="flex-1 min-h-0 p-2" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Session manager
// ─────────────────────────────────────────────────────────────────────────────

interface OpenCodeSessionManagerProps {
  authToken: string | null;
  onSessionSelect: (sessionId: string) => void;
  onOpenProviders?: () => void;
}

export function OpenCodeSessionManager({ authToken, onSessionSelect, onOpenProviders }: OpenCodeSessionManagerProps) {
  const [sessions,     setSessions]     = useState<TerminalSession[]>([]);
  const [loading,      setLoading]      = useState(true);
  const [serverStatus, setServerStatus] = useState<"checking" | "running" | "stopped" | "error">("checking");
  const [creating,     setCreating]     = useState(false);

  const fetchSessions = useCallback(async () => {
    if (!authToken) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/sessions`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) setSessions(await res.json() as TerminalSession[]);
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [authToken]);

  const checkServer = useCallback(async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/status`, {
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        const data = await res.json() as { status: string };
        setServerStatus(data.status === "running" ? "running" : "stopped");
      } else {
        setServerStatus("error");
      }
    } catch {
      setServerStatus("error");
    }
  }, [authToken]);

  const startServer = useCallback(async () => {
    if (!authToken) return;
    setServerStatus("checking");
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/start`, {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}` },
      });
      if (res.ok) {
        setServerStatus("running");
        await fetchSessions();
      } else {
        setServerStatus("error");
      }
    } catch {
      setServerStatus("error");
    }
  }, [authToken, fetchSessions]);

  const createSession = useCallback(async () => {
    if (!authToken) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/sessions`, {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}`, "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const session = await res.json() as TerminalSession;
        onSessionSelect(session.id);
      }
    } catch { /* ignore */ }
    finally { setCreating(false); }
  }, [authToken, onSessionSelect]);

  useEffect(() => {
    checkServer().then(() => fetchSessions());
  }, [checkServer, fetchSessions]);

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#30363d]">
        <span className="text-white text-sm font-medium">OpenCode Sessions</span>
        <div className="flex items-center gap-3">
          {onOpenProviders && (
            <button onClick={onOpenProviders}
              className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#58a6ff] transition-colors">
              <Settings size={13} />Providers
            </button>
          )}
          <span className="flex items-center gap-1.5 text-xs">
            <span className={`w-1.5 h-1.5 rounded-full ${
              serverStatus === "running"  ? "bg-[#3fb950]" :
              serverStatus === "checking" ? "bg-[#d29922] animate-pulse" : "bg-[#f85149]"
            }`} />
            <span className="text-[#8b949e]">{serverStatus}</span>
            {serverStatus !== "running" && serverStatus !== "checking" && (
              <button onClick={startServer} className="text-[#58a6ff] hover:underline ml-1">Start</button>
            )}
          </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader size={20} className="animate-spin text-[#8b949e]" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-[#8b949e] text-sm mb-4">No sessions yet</p>
            <button onClick={createSession} disabled={creating || serverStatus !== "running"}
              className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm rounded-md disabled:opacity-50 transition-colors">
              {creating ? "Creating…" : "New Session"}
            </button>
          </div>
        ) : (
          <>
            {sessions.map(session => (
              <button key={session.id} onClick={() => onSessionSelect(session.id)}
                className="w-full text-left p-3 bg-[#161b22] hover:bg-[#1c2128] border border-[#30363d] rounded-lg transition-colors">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">{session.title || "Untitled session"}</p>
                    <p className="text-xs text-[#8b949e] mt-0.5">{session.id.slice(0, 12)}…</p>
                  </div>
                  <span className="text-xs text-[#8b949e]">{new Date(session.created_at).toLocaleDateString()}</span>
                </div>
              </button>
            ))}
            <button onClick={createSession} disabled={creating || serverStatus !== "running"}
              className="w-full p-3 border border-dashed border-[#30363d] rounded-lg text-[#8b949e] hover:text-white hover:border-[#58a6ff] text-sm transition-colors disabled:opacity-50">
              {creating ? "Creating…" : "+ New Session"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
