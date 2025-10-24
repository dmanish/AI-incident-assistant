import React, { useEffect, useRef, useState } from "react";
import { chat } from "../api";
import type { Session } from "../types";
import MessageInput from "./MessageInput";
import ToolCallsPanel from "./ToolCallsPanel";

type ToolCall =
  | { tool: "ioc_enrich"; ip: string; result: any }
  | { tool: "cve_lookup"; cve: string; result: any }
  | { tool: "log_query"; date: string; username?: string | null; result_count: number }
  | Record<string, any>;

type Msg = {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
};

export default function ChatPane({
  session,
  onLogout,
}: {
  session: Session;
  onLogout: () => void;
}) {
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "assistant",
      content:
        "Ask about policies or run tools.\nExample: “Show me today’s failed login attempts for username jdoe”.",
    },
  ]);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = listRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send(text: string) {
    if (!text.trim()) return;

    // Push the user message immediately
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    try {
      const res = await chat(session.token, text);
      const pretty = res.reply || "(no reply)";
      const toolCalls: ToolCall[] | undefined = Array.isArray(res.tool_calls)
        ? (res.tool_calls as ToolCall[])
        : undefined;

      // Push assistant message with tool_calls preserved
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: pretty, tool_calls: toolCalls },
      ]);
    } catch (e: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Error: " + (e?.message ?? "unknown"),
        },
      ]);
    }
  }

  return (
    <div className="chat-layout">
      <div className="toolbar">
        <div>
          Signed in as <b>{session.email}</b> ({session.role})
        </div>
        <button onClick={onLogout}>Log out</button>
      </div>

      <div className="chat-list" ref={listRef}>
        {messages.map((m, i) => (
          <div key={i} className={`msg ${m.role}`}>
            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{m.content}</pre>

            {/* Render Enrichment panel only for assistant messages that include tool_calls */}
            {m.role === "assistant" && Array.isArray(m.tool_calls) && m.tool_calls.length > 0 && (
              <ToolCallsPanel toolCalls={m.tool_calls} />
            )}
          </div>
        ))}
      </div>

      <MessageInput onSend={send} />
    </div>
  );
}

