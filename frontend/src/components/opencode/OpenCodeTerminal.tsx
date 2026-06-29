"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { Terminal } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import { WebLinksAddon } from "@xterm/addon-web-links";
import "@xterm/xterm/css/xterm.css";

interface TerminalSession {
  id: string;
  title: string;
  created_at: string;
}

interface OpenCodeTerminalProps {
  sessionId: string | null;
  onSessionCreate?: (session: TerminalSession) => void;
  onMessage?: (message: string) => void;
}

const OPENCODE_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function OpenCodeTerminal({
  sessionId,
  onSessionCreate,
  onMessage,
}: OpenCodeTerminalProps) {
  const terminalRef = useRef<HTMLDivElement>(null);
  const termRef = useRef<Terminal | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const fitAddonRef = useRef<FitAddon | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);

  const connectTerminal = useCallback(async (sid: string) => {
    if (!terminalRef.current) return;

    // Dispose existing terminal
    if (termRef.current) {
      termRef.current.dispose();
    }
    if (wsRef.current) {
      wsRef.current.close();
    }

    setIsConnecting(true);

    // Create terminal
    const term = new Terminal({
      theme: {
        background: "#0d1117",
        foreground: "#c9d1d9",
        cursor: "#58a6ff",
        cursorAccent: "#0d1117",
        selectionBackground: "rgba(56, 139, 253, 0.4)",
        black: "#0d1117",
        red: "#ff7b72",
        green: "#3fb950",
        yellow: "#d29922",
        blue: "#58a6ff",
        magenta: "#bc8cff",
        cyan: "#39c5cf",
        white: "#c9d1d9",
        brightBlack: "#484f58",
        brightRed: "#ffa198",
        brightGreen: "#56d364",
        brightYellow: "#e3b341",
        brightBlue: "#79c0ff",
        brightMagenta: "#d2a8ff",
        brightCyan: "#56d4dd",
        brightWhite: "#f0f6fc",
      },
      fontFamily: "'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace",
      fontSize: 14,
      lineHeight: 1.4,
      cursorBlink: true,
      cursorStyle: "bar",
      scrollback: 10000,
      allowProposedApi: true,
    });

    const fitAddon = new FitAddon();
    const webLinksAddon = new WebLinksAddon();

    term.loadAddon(fitAddon);
    term.loadAddon(webLinksAddon);
    term.open(terminalRef.current);

    // Fit to container
    setTimeout(() => fitAddon.fit(), 100);

    termRef.current = term;
    fitAddonRef.current = fitAddon;

    // Write welcome message
    term.writeln("\x1b[1;34m  AgentDesk Terminal\x1b[0m");
    term.writeln("\x1b[90m  Powered by OpenCode\x1b[0m");
    term.writeln("");

    // Connect WebSocket
    const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${wsProtocol}//${window.location.hostname}:8000/api/opencode/ws/${sid}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      setIsConnecting(false);
      term.writeln("\x1b[32m  Connected to OpenCode\x1b[0m");
      term.writeln("");
      term.write("\x1b[1;36m❯\x1b[0m ");
    };

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);

      if (msg.type === "connected") {
        // Already handled
      } else if (msg.type === "message") {
        const data = msg.data;
        if (data?.parts) {
          for (const part of data.parts) {
            if (part.type === "text") {
              term.writeln(part.text);
            }
          }
        }
        term.writeln("");
        term.write("\x1b[1;36m❯\x1b[0m ");
        onMessage?.(JSON.stringify(data));
      } else if (msg.type === "error") {
        term.writeln(`\x1b[31m  Error: ${msg.message}\x1b[0m`);
        term.write("\x1b[1;36m❯\x1b[0m ");
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      term.writeln("\x1b[33m  Disconnected from OpenCode\x1b[0m");
    };

    ws.onerror = () => {
      setIsConnected(false);
      setIsConnecting(false);
      term.writeln("\x1b[31m  Connection failed\x1b[0m");
    };

    // Handle terminal input
    let currentLine = "";
    term.onKey(({ key, domEvent }) => {
      const ev = domEvent;
      const printable = !ev.altKey && !ev.ctrlKey && !ev.metaKey;

      if (ev.key === "Enter") {
        if (currentLine.trim()) {
          ws.send(JSON.stringify({ type: "message", content: currentLine }));
          term.writeln("");
        } else {
          term.write("\r\n\x1b[1;36m❯\x1b[0m ");
        }
        currentLine = "";
      } else if (ev.key === "Backspace") {
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          term.write("\b \b");
        }
      } else if (ev.key === "c" && ev.ctrlKey) {
        // Ctrl+C
        term.writeln("^C");
        currentLine = "";
        term.write("\x1b[1;36m❯\x1b[0m ");
      } else if (ev.key === "l" && ev.ctrlKey) {
        // Ctrl+L - clear
        term.clear();
        term.write("\x1b[1;36m❯\x1b[0m ");
      } else if (printable) {
        currentLine += key;
        term.write(key);
      }
    });

    // Handle resize
    const resizeObserver = new ResizeObserver(() => {
      fitAddon.fit();
    });
    resizeObserver.observe(terminalRef.current);

    return () => {
      resizeObserver.disconnect();
    };
  }, [onMessage]);

  // Connect when sessionId changes
  useEffect(() => {
    if (sessionId) {
      connectTerminal(sessionId);
    }

    return () => {
      if (termRef.current) {
        termRef.current.dispose();
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [sessionId, connectTerminal]);

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 bg-[#161b22] border-b border-[#30363d]">
        <div className="flex items-center gap-3">
          <div className="flex gap-1.5">
            <div className="w-3 h-3 rounded-full bg-[#ff5f57]" />
            <div className="w-3 h-3 rounded-full bg-[#febc2e]" />
            <div className="w-3 h-3 rounded-full bg-[#28c840]" />
          </div>
          <span className="text-sm text-[#8b949e] font-mono">
            AgentDesk Terminal
          </span>
        </div>
        <div className="flex items-center gap-3">
          <span
            className={`text-xs px-2 py-0.5 rounded-full ${
              isConnected
                ? "bg-green-900/50 text-green-400"
                : isConnecting
                  ? "bg-yellow-900/50 text-yellow-400"
                  : "bg-red-900/50 text-red-400"
            }`}
          >
            {isConnected ? "Connected" : isConnecting ? "Connecting..." : "Disconnected"}
          </span>
          <button
            onClick={() => {
              if (fitAddonRef.current) {
                fitAddonRef.current.fit();
              }
            }}
            className="text-xs text-[#8b949e] hover:text-white px-2 py-1 rounded hover:bg-[#30363d]"
          >
            Fit
          </button>
        </div>
      </div>

      {/* Terminal Container */}
      <div
        ref={terminalRef}
        className="flex-1 p-2 overflow-hidden"
        style={{ minHeight: 0 }}
      />

      {/* Status Bar */}
      <div className="flex items-center justify-between px-4 py-1 bg-[#161b22] border-t border-[#30363d] text-xs text-[#8b949e]">
        <span>OpenCode Agent</span>
        <span>Session: {sessionId?.slice(0, 8) || "none"}</span>
      </div>
    </div>
  );
}

// Helper component for creating new sessions
export function OpenCodeSessionManager({
  onSessionSelect,
}: {
  onSessionSelect: (sessionId: string) => void;
}) {
  const [sessions, setSessions] = useState<TerminalSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [serverStatus, setServerStatus] = useState<string>("checking");

  useEffect(() => {
    checkStatus();
    loadSessions();
  }, []);

  const checkStatus = async () => {
    try {
      const resp = await fetch(`${OPENCODE_API}/api/opencode/status`);
      const data = await resp.json();
      setServerStatus(data.status);
      if (data.status !== "running") {
        // Auto-start server
        await startServer();
      }
    } catch {
      setServerStatus("unreachable");
    }
  };

  const startServer = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${OPENCODE_API}/api/opencode/start`, {
        method: "POST",
      });
      const data = await resp.json();
      setServerStatus(data.status === "started" || data.status === "already_running" ? "running" : "failed");
      if (data.status === "started" || data.status === "already_running") {
        await loadSessions();
      }
    } catch {
      setServerStatus("unreachable");
    } finally {
      setLoading(false);
    }
  };

  const loadSessions = async () => {
    try {
      const resp = await fetch(`${OPENCODE_API}/api/opencode/sessions`);
      if (resp.ok) {
        const data = await resp.json();
        setSessions(Array.isArray(data) ? data : []);
      }
    } catch {
      // Server might not be ready yet
    }
  };

  const createSession = async () => {
    setLoading(true);
    try {
      const resp = await fetch(`${OPENCODE_API}/api/opencode/sessions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: `AgentDesk Session` }),
      });
      const data = await resp.json();
      if (data.id) {
        setSessions((prev) => [data, ...prev]);
        onSessionSelect(data.id);
      }
    } catch (err) {
      console.error("Failed to create session:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-[#0d1117]">
      {/* Header */}
      <div className="px-4 py-3 bg-[#161b22] border-b border-[#30363d]">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-white font-medium">OpenCode Sessions</h3>
            <p className="text-xs text-[#8b949e] mt-0.5">
              AI coding agent terminal
            </p>
          </div>
          <button
            onClick={createSession}
            disabled={loading || serverStatus !== "running"}
            className="px-3 py-1.5 bg-[#238636] hover:bg-[#2ea043] text-white text-sm rounded-md disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {loading ? "Starting..." : "New Session"}
          </button>
        </div>
      </div>

      {/* Server Status */}
      <div className="px-4 py-2 bg-[#161b22] border-b border-[#30363d]">
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${
              serverStatus === "running"
                ? "bg-green-500"
                : serverStatus === "checking"
                  ? "bg-yellow-500 animate-pulse"
                  : "bg-red-500"
            }`}
          />
          <span className="text-[#8b949e]">
            Server: {serverStatus}
            {serverStatus !== "running" && serverStatus !== "checking" && (
              <button
                onClick={startServer}
                className="ml-2 text-blue-400 hover:underline"
              >
                Retry
              </button>
            )}
          </span>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {sessions.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-[#8b949e] mb-4">No sessions yet</p>
            <button
              onClick={createSession}
              disabled={loading || serverStatus !== "running"}
              className="px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-md disabled:opacity-50"
            >
              Create Your First Session
            </button>
          </div>
        ) : (
          sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => onSessionSelect(session.id)}
              className="w-full text-left p-3 bg-[#161b22] hover:bg-[#1c2128] border border-[#30363d] rounded-lg transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white text-sm font-medium">
                    {session.title || "Untitled Session"}
                  </p>
                  <p className="text-xs text-[#8b949e] mt-0.5">
                    {session.id.slice(0, 12)}...
                  </p>
                </div>
                <span className="text-xs text-[#8b949e]">
                  {new Date(session.created_at).toLocaleDateString()}
                </span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  );
}
