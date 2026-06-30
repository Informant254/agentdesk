"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";

const OpenCodeTerminal = dynamic(
  () => import("./OpenCodeTerminal").then((m) => m.OpenCodeTerminal),
  { ssr: false }
);

const OpenCodeSessionManager = dynamic(
  () => import("./OpenCodeTerminal").then((m) => m.OpenCodeSessionManager),
  { ssr: false }
);

type View = "sessions" | "terminal";

export function OpenCodePanel() {
  const [view, setView] = useState<View>("sessions");
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const handleSessionSelect = useCallback((sessionId: string) => {
    setActiveSessionId(sessionId);
    setView("terminal");
  }, []);

  const handleBack = useCallback(() => {
    setView("sessions");
  }, []);

  if (view === "terminal" && activeSessionId) {
    return (
      <div className="flex flex-col h-full">
        <div className="flex items-center gap-3 px-4 py-2 bg-[#161b22] border-b border-[#30363d]">
          <button
            onClick={handleBack}
            className="text-[#8b949e] hover:text-white text-sm"
          >
            ← Sessions
          </button>
          <span className="text-[#30363d]">|</span>
          <span className="text-white text-sm font-medium">OpenCode Terminal</span>
        </div>
        <div className="flex-1 min-h-0">
          <OpenCodeTerminal sessionId={activeSessionId} />
        </div>
      </div>
    );
  }

  return <OpenCodeSessionManager onSessionSelect={handleSessionSelect} />;
}
