import React, { useRef, useEffect, useState } from 'react';
import './AgentResponseDualPane.css';

interface ReasoningStep {
  step: number;
  type: string;
  tool_name?: string;
  description: string;
  arguments?: Record<string, any>;
  success?: boolean;
  result_preview?: string;
  llm_reasoning?: string;
  warning?: boolean;
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
}

interface Props {
  response: AgentResponse;
}

export default function AgentResponseDualPane({ response }: Props) {
  const answerPaneRef = useRef<HTMLDivElement>(null);
  const reasoningPaneRef = useRef<HTMLDivElement>(null);
  const [syncSource, setSyncSource] = useState<'answer' | 'reasoning' | null>(null);

  // Synchronized scrolling
  useEffect(() => {
    const answerPane = answerPaneRef.current;
    const reasoningPane = reasoningPaneRef.current;

    if (!answerPane || !reasoningPane) return;

    const handleAnswerScroll = () => {
      if (syncSource === 'reasoning') return;
      setSyncSource('answer');

      const scrollPercentage = answerPane.scrollTop / (answerPane.scrollHeight - answerPane.clientHeight);
      reasoningPane.scrollTop = scrollPercentage * (reasoningPane.scrollHeight - reasoningPane.clientHeight);

      // Clear sync source after a short delay
      setTimeout(() => setSyncSource(null), 50);
    };

    const handleReasoningScroll = () => {
      if (syncSource === 'answer') return;
      setSyncSource('reasoning');

      const scrollPercentage = reasoningPane.scrollTop / (reasoningPane.scrollHeight - reasoningPane.clientHeight);
      answerPane.scrollTop = scrollPercentage * (answerPane.scrollHeight - answerPane.clientHeight);

      // Clear sync source after a short delay
      setTimeout(() => setSyncSource(null), 50);
    };

    answerPane.addEventListener('scroll', handleAnswerScroll);
    reasoningPane.addEventListener('scroll', handleReasoningScroll);

    return () => {
      answerPane.removeEventListener('scroll', handleAnswerScroll);
      reasoningPane.removeEventListener('scroll', handleReasoningScroll);
    };
  }, [syncSource]);

  // Auto-scroll to bottom on new response
  useEffect(() => {
    if (answerPaneRef.current) {
      answerPaneRef.current.scrollTop = 0;
    }
    if (reasoningPaneRef.current) {
      reasoningPaneRef.current.scrollTop = 0;
    }
  }, [response]);

  return (
    <div className="agent-response-container">
      {/* Header with routes used */}
      <div className="response-header">
        <div className="routes-badge">
          <span className="badge-title">Agent Routes:</span>
          {response.routes_used.llm_calls > 0 && (
            <span className="route-tag llm">
              🤖 LLM ({response.routes_used.llm_calls})
            </span>
          )}
          {response.routes_used.rag_searches > 0 && (
            <span className="route-tag rag">
              📚 RAG ({response.routes_used.rag_searches})
            </span>
          )}
          {response.routes_used.log_queries > 0 && (
            <span className="route-tag logs">
              📊 Logs ({response.routes_used.log_queries})
            </span>
          )}
          <span className="iterations-tag">
            {response.iterations} {response.iterations === 1 ? 'iteration' : 'iterations'}
          </span>
        </div>
      </div>

      {/* Dual pane container */}
      <div className="dual-pane-container">
        {/* Left pane: Answer */}
        <div className="pane answer-pane" ref={answerPaneRef}>
          <div className="pane-header">
            <h3>💬 Response</h3>
            <span className="pane-hint">Scroll to see reasoning →</span>
          </div>
          <div className="pane-content">
            <div className="answer-text">
              {response.reply}
            </div>

            {/* Visual markers aligned with steps */}
            {response.reasoning_steps.map((step, idx) => (
              <div key={idx} className="answer-marker" data-step={step.step}>
                <div className="marker-line"></div>
              </div>
            ))}
          </div>
        </div>

        {/* Divider */}
        <div className="pane-divider">
          <div className="divider-line"></div>
          <div className="divider-icon">⇄</div>
        </div>

        {/* Right pane: Reasoning */}
        <div className="pane reasoning-pane" ref={reasoningPaneRef}>
          <div className="pane-header">
            <h3>🧠 Agent Reasoning</h3>
            <span className="pane-hint">← Synced with response</span>
          </div>
          <div className="pane-content">
            {response.reasoning_steps.map((step, idx) => (
              <div
                key={idx}
                className={`reasoning-step ${step.type} ${step.warning ? 'warning' : ''}`}
                data-step={step.step}
              >
                <div className="step-header">
                  <span className="step-number">Step {step.step}</span>
                  <span className="step-type">
                    {step.type === 'tool_call' && '🔧'}
                    {step.type === 'final_answer' && '🧠'}
                    {step.type === 'max_iterations' && '⚠️'}
                  </span>
                </div>

                <div className="step-description">
                  {step.description}
                </div>

                {step.tool_name && (
                  <div className="tool-info">
                    <div className="tool-name">
                      <strong>Tool:</strong> {step.tool_name}
                    </div>
                    {step.arguments && (
                      <div className="tool-arguments">
                        <strong>Parameters:</strong>
                        <pre>{JSON.stringify(step.arguments, null, 2)}</pre>
                      </div>
                    )}
                  </div>
                )}

                {step.result_preview && (
                  <div className="result-preview">
                    <strong>Result:</strong>
                    <div className="preview-text">{step.result_preview}</div>
                  </div>
                )}

                {step.llm_reasoning && (
                  <div className="llm-reasoning">
                    <strong>LLM Reasoning:</strong>
                    <div className="reasoning-text">{step.llm_reasoning}</div>
                  </div>
                )}

                {step.success !== undefined && (
                  <div className={`step-status ${step.success ? 'success' : 'error'}`}>
                    {step.success ? '✓ Success' : '✗ Failed'}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Footer with metadata */}
      <div className="response-footer">
        <details className="metadata-details">
          <summary>📊 Technical Details</summary>
          <div className="metadata-content">
            <div className="metadata-row">
              <span className="label">Model:</span>
              <span className="value">{response.metadata.model}</span>
            </div>
            <div className="metadata-row">
              <span className="label">Total LLM Calls:</span>
              <span className="value">{response.metadata.total_llm_calls}</span>
            </div>
            <div className="metadata-row">
              <span className="label">Tools Used:</span>
              <div className="tools-list">
                {response.routes_used.tools_used.map((tool, idx) => (
                  <span key={idx} className="tool-chip">
                    {tool.replace(/_/g, ' ')}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </details>
      </div>
    </div>
  );
}
