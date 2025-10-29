import React, { useEffect, useRef, useState } from "react";
import { agentChatV2 } from "../api";
import type { Session } from "../types";
import MessageInput from "./MessageInput";
import ToolCallsPanel from "./ToolCallsPanel";
import AgentResponseDualPane from "./AgentResponseDualPane";

type ToolCall =
  | { tool: "ioc_enrich"; ip: string; result: any }
  | { tool: "cve_lookup"; cve: string; result: any }
  | { tool: "log_query"; date: string; username?: string | null; result_count: number }
  | Record<string, any>;

interface ReasoningStep {
  step: number;
  type: string;
  tool_name?: string;
  description: string;
  arguments?: Record<string, any>;
  success?: boolean;
  result_preview?: string;
  llm_reasoning?: string;
}

interface RoutesUsed {
  llm_calls: number;
  rag_searches: number;
  log_queries: number;
  tools_used: string[];
}

interface Metadata {
  model: string;
  total_llm_calls: number;
  used_rag: boolean;
  used_logs: boolean;
}

interface AgentResponse {
  reply: string;
  reasoning_steps: ReasoningStep[];
  routes_used: RoutesUsed;
  metadata: Metadata;
  iterations: number;
  convo_id?: string;
  tool_calls?: ToolCall[];
}

type Msg = {
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  agent_response?: AgentResponse;
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
        "Ask about policies or run tools.\nExample: \"Show me today's failed login attempts for username jdoe\".",
    },
  ]);
  const [convoId, setConvoId] = useState<string | undefined>(undefined);
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
      // Use the new function calling agent with conversation history
      const res = await agentChatV2(session.token, text, convoId);

      // Update conversation ID for multi-turn conversations
      if (res.convo_id) {
        setConvoId(res.convo_id);
      }

      const pretty = res.reply || "(no reply)";
      const toolCalls: ToolCall[] | undefined = Array.isArray(res.tool_calls)
        ? (res.tool_calls as ToolCall[])
        : undefined;

      // Check if we have enhanced agent response data
      const hasAgentData = res.reasoning_steps && res.routes_used && res.metadata;

      // Push assistant message with full agent response
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: pretty,
          tool_calls: toolCalls,
          agent_response: hasAgentData ? res : undefined,
        },
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
            {/* Show user messages as before */}
            {m.role === "user" && (
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{m.content}</pre>
            )}

            {/* For assistant messages, check if we have enhanced agent data */}
            {m.role === "assistant" && (
              <>
                {/* If we have enhanced agent response data, use the dual-pane component */}
                {m.agent_response?.reasoning_steps && m.agent_response?.routes_used && m.agent_response?.metadata ? (
                  <AgentResponseDualPane response={m.agent_response} />
                ) : (
                  /* Otherwise, show simple text response */
                  <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{m.content}</pre>
                )}

                {/* Render legacy tool calls panel if no agent data but has tool_calls */}
                {!m.agent_response && Array.isArray(m.tool_calls) && m.tool_calls.length > 0 && (
                  <ToolCallsPanel toolCalls={m.tool_calls} />
                )}
              </>
            )}
          </div>
        ))}
      </div>

      <MessageInput onSend={send} />
    </div>
  );
}

