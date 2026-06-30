import type { Metadata } from "next";
import "./globals.css";
import "@xterm/xterm/css/xterm.css";

export const metadata: Metadata = {
  title: "AgentDesk - AI Assistant for Trades Businesses",
  description:
    "Autonomous AI agent that handles scheduling, dispatch, and invoicing for HVAC, plumbing, electrical, and other trades businesses.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}