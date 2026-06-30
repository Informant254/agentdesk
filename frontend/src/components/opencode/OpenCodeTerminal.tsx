"use client";

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

// Derive the API base from env (falls back to Render URL)
const API_HTTP = process.env.NEXT_PUBLIC_API_URL || "https://agentdesk-mzx6.onrender.com";
const API_WS   = API_HTTP.replace(/^https?:\/\//, m => (m === "https://" ? "wss://" : "ws://"));

export function OpenCodeTerminal({ sessionId, authToken, onOpenProviders }: OpenCodeTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef     = useRef<unknown>(null);
  const wsRef       = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<unknown>(null);

  const [isConnected,  setIsConnected]  = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectedProviders, setConnectedProviders] = useState<string[]>([]);

  const connectTerminal = useCallback(async (sid: string) => {
    if (!terminalRef.current || !authToken) return;

    const { Terminal }     = await import("@xterm/xterm");
    const { FitAddon }     = await import("@xterm/addon-fit");
    const { WebLinksAddon} = await import("@xterm/addon-web-links");

    // Dispose existing
    if (termRef.current)  (termRef.current as { dispose(): void }).dispose();
    if (wsRef.current)    wsRef.current.close();

    setIsConnecting(true);

    const term = new Terminal({
      theme: {
        background:          "#0d1117",
        foreground:          "#c9d1d9",
        cursor:              "#58a6ff",
        cursorAccent:        "#0d1117",
        selectionBackground: "rgba(56,139,253,0.4)",
        black:   "#0d1117", red:     "#ff7b72", green:   "#3fb950",
        yellow:  "#d29922",  blue:    "#58a6ff", magenta: "#bc8cff",
        cyan:    "#39c5cf",  white:   "#c9d1d9",
        brightBlack:   "#484f58", brightRed:     "#ffa198",
        brightGreen:   "#56d364", brightYellow:  "#e3b341",
        brightBlue:    "#79c0ff", brightMagenta: "#d2a8ff",
        brightCyan:    "#56d4dd", brightWhite:   "#f0f6fc",
      },
      fontFamily:      "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      fontSize:        14,
      lineHeight:      1.4,
      cursorBlink:     true,
      cursorStyle:     "bar",
      scrollback:      10000,
      allowProposedApi: true,
    });

    const fitAddon     = new FitAddon();
    const webLinksAddon = new WebLinksAddon();
    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(terminalRef.current);
    setTimeout(() => fitAddon.fit(), 100);

    termRef.current    = term;
    fitAddonRef.current = fitAddon;

    term.writeln("\x1b[1;34m  AgentDesk Terminal\x1b[0m");
    term.writeln("\x1b[90m  Powered by OpenCode — connecting…\x1b[0m");
    term.writeln("");

    // ── WebSocket ──────────────────────────────────────────────────────
    const ws = new WebSocket(`${API_WS}/api/opencode/ws/${sid}`);
    wsRef.current = ws;

    ws.onopen = () => {
      // Send auth as first message
      ws.send(JSON.stringify({ type: "auth", token: authToken }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);

        if (msg.type === "connected") {
          setIsConnected(true);
          setIsConnecting(false);
          setConnectedProviders(msg.providers || []);
          term.writeln("\x1b[32m  ✓ Connected to OpenCode\x1b[0m");
          if (msg.providers?.length > 0) {
            term.writeln(`\x1b[90m  Providers: ${msg.providers.join(", ")}\x1b[0m`);
          } else {
            term.writeln("\x1b[33m  ⚠ No providers configured — go to AI Providers to add your API keys\x1b[0m");
          }
          term.writeln("");
          term.write("\x1b[1;36m❯\x1b[0m ");
          return;
        }

        if (msg.type === "message") {
          const data = msg.data;
          if (data?.parts) {
            for (const part of data.parts) {
              if (part.type === "text") {
                const lines = part.text.split("\n");
                for (const line of lines) term.writeln(line);
              }
            }
          }
          term.writeln("");
          term.write("\x1b[1;36m❯\x1b[0m ");
          return;
        }

        if (msg.type === "error") {
          term.writeln(`\x1b[31m  ✗ ${msg.message}\x1b[0m`);
          term.write("\x1b[1;36m❯\x1b[0m ");
          return;
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      if (termRef.current) {
        term.writeln("\n\x1b[33m  Connection closed\x1b[0m");
      }
    };

    ws.onerror = () => {
      setIsConnected(false);
      setIsConnecting(false);
      term.writeln("\x1b[31m  Failed to connect to OpenCode server\x1b[0m");
      term.write("\x1b[1;36m❯\x1b[0m ");
    };

    // ── Input handling ─────────────────────────────────────────────────
    let inputBuffer = "";
    term.onKey(({ key, domEvent }) => {
      const code = domEvent.keyCode;

      if (code === 13) {
        // Enter — send message
        const content = inputBuffer.trim();
        term.writeln("");
        inputBuffer = "";
        if (content && ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({ type: "message", content }));
        } else {
          term.write("\x1b[1;36m❯\x1b[0m ");
        }
      } else if (code === 8) {
        // Backspace
        if (inputBuffer.length > 0) {
          inputBuffer = inputBuffer.slice(0, -1);
          term.write("\b \b");
        }
      } else if (key) {
        inputBuffer += key;
        term.write(key);
      }
    });

    // ── Resize observer ─────────────────────────────────────────────────
    const ro = new ResizeObserver(() => {
      try { (fitAddonRef.current as { fit(): void })?.fit(); } catch {}
    });
    if (terminalRef.current) ro.observe(terminalRef.current);

    return () => {
      ro.disconnect();
      ws.close();
      term.dispose();
    };
  }, [authToken]);

  useEffect(() => {
    const cleanup = connectTerminal(sessionId);
    return () => { cleanup?.then(fn => fn?.()); };
  }, [sessionId, connectTerminal]);

  const handleReconnect = () => connectTerminal(sessionId);

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Status bar */}
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
            <button
              onClick={onOpenProviders}
              className="flex items-center gap-1 px-2 py-0.5 bg-[#d29922]/20 text-[#d29922] rounded hover:bg-[#d29922]/30 transition-colors"
            >
              <Settings size={11} />
              Add API keys
            </button>
          )}
          <button
            onClick={handleReconnect}
            className="flex items-center gap-1 text-[#8b949e] hover:text-white transition-colors"
          >
            <RefreshCw size={12} />
            Reconnect
          </button>
        </div>
      </div>

      {/* Terminal */}
      <div ref={terminalRef} className="flex-1 min-h-0 p-2" />
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────────
// Session manager component
// ─────────────────────────────────────────────────────────────────────────────

interface OpenCodeSessionManagerProps {
  authToken: string | null;
  onSessionSelect: (sessionId: string) => void;
  onOpenProviders?: () => void;
}

export function OpenCodeSessionManager({
  authToken,
  onSessionSelect,
  onOpenProviders,
}: OpenCodeSessionManagerProps) {
  const [sessions,      setSessions]      = useState<TerminalSession[]>([]);
  const [loading,       setLoading]       = useState(true);
  const [serverStatus,  setServerStatus]  = useState<"checking" | "running" | "stopped" | "error">("checking");
  const [creating,      setCreating]      = useState(false);

  const headers = authToken ? { Authorization: `Bearer ${authToken}` } : {};

  const checkServer = useCallback(async () => {
    if (!authToken) return;
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/status`, { headers });
      if (res.ok) {
        const data = await res.json();
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
      const res = await fetch(`${API_HTTP}/api/opencode/start`, { method: "POST", headers });
      if (res.ok) {
        setServerStatus("running");
        fetchSessions();
      } else {
        setServerStatus("error");
      }
    } catch {
      setServerStatus("error");
    }
  }, [authToken]);

  const fetchSessions = useCallback(async () => {
    if (!authToken) return;
    setLoading(true);
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/sessions`, { headers });
      if (res.ok) setSessions(await res.json());
    } catch {}
    finally { setLoading(false); }
  }, [authToken]);

  const createSession = useCallback(async () => {
    if (!authToken) return;
    setCreating(true);
    try {
      const res = await fetch(`${API_HTTP}/api/opencode/sessions`, {
        method: "POST",
        headers: { ...headers, "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (res.ok) {
        const session = await res.json();
        onSessionSelect(session.id);
      }
    } catch {}
    finally { setCreating(false); }
  }, [authToken, onSessionSelect]);

  useEffect(() => {
    checkServer().then(() => fetchSessions());
  }, [checkServer, fetchSessions]);

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#30363d]">
        <span className="text-white text-sm font-medium">OpenCode Sessions</span>
        <div className="flex items-center gap-3">
          {onOpenProviders && (
            <button
              onClick={onOpenProviders}
              className="flex items-center gap-1.5 text-xs text-[#8b949e] hover:text-[#58a6ff] transition-colors"
            >
              <Settings size={13} />
              Providers
            </button>
          )}
          <span className="flex items-center gap-1.5 text-xs">
            <span className={`w-1.5 h-1.5 rounded-full ${
              serverStatus === "running" ? "bg-[#3fb950]"
              : serverStatus === "checking" ? "bg-[#d29922] animate-pulse"
              : "bg-[#f85149]"
            }`} />
            <span className="text-[#8b949e]">{serverStatus}</span>
            {serverStatus !== "running" && serverStatus !== "checking" && (
              <button onClick={startServer} className="text-[#58a6ff] hover:underline ml-1">
                Start
              </button>
            )}
          </span>
        </div>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader size={20} className="animate-spin text-[#8b949e]" />
          </div>
        ) : sessions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-[#8b949e] text-sm mb-4">No sessions yet</p>
            <button
              onClick={createSession}
              disabled={creating || serverStatus !== "running"}
              className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white text-sm rounded-md disabled:opacity-50 transition-colors"
            >
              {creating ? "Creating…" : "New Session"}
            </button>
          </div>
        ) : (
          <>
            {sessions.map(session => (
              <button
                key={session.id}
                onClick={() => onSessionSelect(session.id)}
                className="w-full text-left p-3 bg-[#161b22] hover:bg-[#1c2128] border border-[#30363d] rounded-lg transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-white text-sm font-medium">{session.title || "Untitled session"}</p>
                    <p className="text-xs text-[#8b949e] mt-0.5">{session.id.slice(0, 12)}…</p>
                  </div>
                  <span className="text-xs text-[#8b949e]">
                    {new Date(session.created_at).toLocaleDateString()}
                  </span>
                </div>
              </button>
            ))}
            <button
              onClick={createSession}
              disabled={creating || serverStatus !== "running"}
              className="w-full p-3 border border-dashed border-[#30363d] rounded-lg text-[#8b949e] hover:text-white hover:border-[#58a6ff] text-sm transition-colors disabled:opacity-50"
            >
              {creating ? "Creating…" : "+ New Session"}
            </button>
          </>
        )}
      </div>
    </div>
  );
}
