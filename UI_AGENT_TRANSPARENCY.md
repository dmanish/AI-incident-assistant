# UI Components for Agent Transparency

## Overview

The enhanced `/agent/chat/v2` endpoint now returns detailed information about the agent's reasoning process, enabling rich UI visualizations that show users:
- What steps the agent took
- Which tools were used
- Why certain decisions were made
- Routes taken (LLM, RAG, log queries)

## Response Structure

```json
{
  "reply": "Final answer...",
  "convo_id": "uuid",
  "iterations": 2,
  "agent_type": "function_calling",

  // NEW: Reasoning transparency
  "reasoning_steps": [
    {
      "step": 1,
      "type": "tool_call",
      "tool_name": "query_failed_logins",
      "description": "Queried authentication logs for failed login attempts",
      "arguments": {"date": "2025-10-28", "username": "jdoe"},
      "success": true,
      "result_preview": "Found 50 failed login attempts..."
    },
    {
      "step": 2,
      "type": "final_answer",
      "description": "Agent synthesized final answer",
      "llm_reasoning": "Based on the log data..."
    }
  ],

  // NEW: Routes used
  "routes_used": {
    "llm_calls": 2,
    "rag_searches": 1,
    "log_queries": 1,
    "tools_used": ["query_failed_logins", "search_knowledge_base"]
  },

  // NEW: Metadata
  "metadata": {
    "model": "gpt-4o-mini",
    "total_llm_calls": 2,
    "used_rag": true,
    "used_logs": true
  }
}
```

## UI Component Suggestions

### 1. Agent Steps Timeline

A visual timeline showing each step the agent took:

```
┌─────────────────────────────────────────────────────────┐
│  Agent Reasoning Process (2 iterations)                 │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Step 1: 🔍 Query Tool                                  │
│  ├─ Searched authentication logs                       │
│  ├─ Parameters: date=2025-10-28, username=jdoe        │
│  └─ Result: Found 50 failed login attempts            │
│                                                         │
│  Step 2: 🧠 Final Answer                                │
│  └─ Synthesized response from gathered data           │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

**React Component Example:**
```tsx
interface ReasoningStep {
  step: number;
  type: string;
  tool_name?: string;
  description: string;
  arguments?: Record<string, any>;
  success?: boolean;
  result_preview?: string;
}

function AgentStepsTimeline({ steps }: { steps: ReasoningStep[] }) {
  return (
    <div className="agent-timeline">
      <h3>Agent Reasoning Process</h3>
      {steps.map((step, idx) => (
        <div key={idx} className={`timeline-step step-${step.type}`}>
          <div className="step-icon">
            {step.type === 'tool_call' && '🔧'}
            {step.type === 'final_answer' && '🧠'}
          </div>
          <div className="step-content">
            <h4>Step {step.step}: {step.description}</h4>

            {step.tool_name && (
              <div className="tool-info">
                <span className="tool-name">{step.tool_name}</span>
                {step.arguments && (
                  <pre className="arguments">
                    {JSON.stringify(step.arguments, null, 2)}
                  </pre>
                )}
              </div>
            )}

            {step.result_preview && (
              <div className="result-preview">
                {step.result_preview}
              </div>
            )}

            {step.success !== undefined && (
              <span className={`status ${step.success ? 'success' : 'error'}`}>
                {step.success ? '✓ Success' : '✗ Failed'}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
```

**CSS:**
```css
.agent-timeline {
  background: #f8f9fa;
  border-radius: 8px;
  padding: 16px;
  margin: 16px 0;
}

.timeline-step {
  display: flex;
  gap: 12px;
  padding: 12px;
  margin: 8px 0;
  background: white;
  border-left: 3px solid #007bff;
  border-radius: 4px;
}

.step-icon {
  font-size: 24px;
}

.tool-info {
  background: #f0f0f0;
  padding: 8px;
  border-radius: 4px;
  margin-top: 8px;
}

.arguments {
  font-size: 12px;
  background: #2d2d2d;
  color: #f0f0f0;
  padding: 8px;
  border-radius: 4px;
  margin-top: 4px;
}

.status.success {
  color: #28a745;
}

.status.error {
  color: #dc3545;
}
```

### 2. Routes Used Badge

Show which capabilities were used in a compact badge format:

```
┌────────────────────────────────────┐
│ Routes Used:                      │
│ ● LLM (2 calls)                   │
│ ● RAG (1 search)                  │
│ ● Logs (1 query)                  │
└────────────────────────────────────┘
```

**React Component:**
```tsx
interface RoutesUsed {
  llm_calls: number;
  rag_searches: number;
  log_queries: number;
  tools_used: string[];
}

function RoutesUsedBadge({ routes }: { routes: RoutesUsed }) {
  return (
    <div className="routes-badge">
      <h4>Routes Used</h4>
      <div className="route-items">
        {routes.llm_calls > 0 && (
          <span className="route-item llm">
            <span className="icon">🤖</span>
            LLM ({routes.llm_calls} {routes.llm_calls === 1 ? 'call' : 'calls'})
          </span>
        )}

        {routes.rag_searches > 0 && (
          <span className="route-item rag">
            <span className="icon">📚</span>
            RAG ({routes.rag_searches} {routes.rag_searches === 1 ? 'search' : 'searches'})
          </span>
        )}

        {routes.log_queries > 0 && (
          <span className="route-item logs">
            <span className="icon">📊</span>
            Logs ({routes.log_queries} {routes.log_queries === 1 ? 'query' : 'queries'})
          </span>
        )}
      </div>

      {routes.tools_used.length > 0 && (
        <div className="tools-used">
          <span>Tools: </span>
          {routes.tools_used.map((tool, idx) => (
            <span key={idx} className="tool-tag">
              {tool.replace('_', ' ')}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
```

**CSS:**
```css
.routes-badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 12px;
  border-radius: 8px;
  margin: 8px 0;
}

.route-items {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}

.route-item {
  background: rgba(255, 255, 255, 0.2);
  padding: 6px 12px;
  border-radius: 16px;
  font-size: 14px;
}

.tool-tag {
  background: rgba(255, 255, 255, 0.3);
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 12px;
  margin-left: 4px;
}
```

### 3. Expandable Details Panel

A collapsible panel showing detailed agent activity:

```
┌────────────────────────────────────────┐
│ Agent Details ▼                        │
├────────────────────────────────────────┤
│ Model: gpt-4o-mini                     │
│ Iterations: 2                          │
│ LLM Calls: 2                           │
│ Tools Used: query_failed_logins, RAG   │
│                                        │
│ [View Full Reasoning] [View Audit Log] │
└────────────────────────────────────────┘
```

**React Component:**
```tsx
interface Metadata {
  model: string;
  total_llm_calls: number;
  used_rag: boolean;
  used_logs: boolean;
}

function AgentDetailsPanel({
  metadata,
  iterations,
  routes
}: {
  metadata: Metadata;
  iterations: number;
  routes: RoutesUsed;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="agent-details-panel">
      <button
        className="panel-toggle"
        onClick={() => setExpanded(!expanded)}
      >
        Agent Details {expanded ? '▲' : '▼'}
      </button>

      {expanded && (
        <div className="panel-content">
          <div className="detail-row">
            <span className="label">Model:</span>
            <span className="value">{metadata.model}</span>
          </div>

          <div className="detail-row">
            <span className="label">Iterations:</span>
            <span className="value">{iterations}</span>
          </div>

          <div className="detail-row">
            <span className="label">LLM Calls:</span>
            <span className="value">{metadata.total_llm_calls}</span>
          </div>

          <div className="detail-row">
            <span className="label">Capabilities Used:</span>
            <div className="capabilities">
              {metadata.used_rag && <span className="capability-tag">RAG</span>}
              {metadata.used_logs && <span className="capability-tag">Log Query</span>}
            </div>
          </div>

          <div className="detail-row">
            <span className="label">Tools:</span>
            <div className="tools">
              {routes.tools_used.map((tool, idx) => (
                <span key={idx} className="tool-chip">
                  {tool}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

### 4. Visual Flow Diagram

For complex multi-step queries, show a flow diagram:

```
User Query
    │
    ├─→ [LLM Decision] ─→ Tool: query_failed_logins
    │                      ↓
    │                   Result: 50 attempts
    │                      ↓
    ├─→ [LLM Decision] ─→ Tool: search_knowledge_base
    │                      ↓
    │                   Result: Security policy
    │                      ↓
    └─→ [LLM Synthesis] ─→ Final Answer
```

### 5. Iteration Progress Indicator

Show iterations as a progress bar:

```
┌──────────────────────────────────────┐
│ Iteration 2 of 5                     │
│ ████████░░░░░░░░░░  40%              │
└──────────────────────────────────────┘
```

**React Component:**
```tsx
function IterationProgress({
  current,
  max
}: {
  current: number;
  max: number;
}) {
  const percentage = (current / max) * 100;

  return (
    <div className="iteration-progress">
      <div className="progress-text">
        Iteration {current} of {max}
      </div>
      <div className="progress-bar">
        <div
          className="progress-fill"
          style={{ width: `${percentage}%` }}
        />
      </div>
      <div className="progress-percentage">
        {percentage.toFixed(0)}%
      </div>
    </div>
  );
}
```

## Complete UI Example

Here's how it all comes together in the chat interface:

```tsx
function AgentResponse({ response }: { response: AgentChatResponse }) {
  return (
    <div className="agent-response">
      {/* Main answer */}
      <div className="answer-text">
        {response.reply}
      </div>

      {/* Compact routes badge */}
      <RoutesUsedBadge routes={response.routes_used} />

      {/* Expandable sections */}
      <details>
        <summary>🔍 View Agent Reasoning ({response.reasoning_steps.length} steps)</summary>
        <AgentStepsTimeline steps={response.reasoning_steps} />
      </details>

      <details>
        <summary>📊 View Technical Details</summary>
        <AgentDetailsPanel
          metadata={response.metadata}
          iterations={response.iterations}
          routes={response.routes_used}
        />
      </details>

      {/* Tool calls if any */}
      {response.tool_calls.length > 0 && (
        <details>
          <summary>🔧 View Tool Calls ({response.tool_calls.length})</summary>
          <ToolCallsList calls={response.tool_calls} />
        </details>
      )}
    </div>
  );
}
```

## Mobile-Friendly Version

For mobile, use a simpler accordion layout:

```tsx
function AgentResponseMobile({ response }: { response: AgentChatResponse }) {
  return (
    <div className="agent-response-mobile">
      <div className="answer">{response.reply}</div>

      <div className="quick-stats">
        <span className="stat">
          {response.routes_used.llm_calls} LLM calls
        </span>
        <span className="stat">
          {response.iterations} iterations
        </span>
        {response.metadata.used_rag && (
          <span className="stat">Used RAG</span>
        )}
      </div>

      <button className="view-details-btn">
        View Reasoning Steps
      </button>
    </div>
  );
}
```

## API Integration Example

```tsx
import { useState } from 'react';

function ChatInterface() {
  const [response, setResponse] = useState<AgentChatResponse | null>(null);

  async function sendMessage(message: string) {
    const res = await fetch('/agent/chat/v2', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ message })
    });

    const data = await res.json();
    setResponse(data);
  }

  return (
    <div>
      {/* Chat UI */}
      {response && (
        <AgentResponse response={response} />
      )}
    </div>
  );
}
```

## Accessibility Considerations

1. **Screen readers**: Add proper ARIA labels to all interactive elements
2. **Keyboard navigation**: Ensure all expandable sections are keyboard accessible
3. **Color contrast**: Use high-contrast colors for text and badges
4. **Focus indicators**: Clear visual feedback for focused elements

```tsx
<details>
  <summary
    role="button"
    aria-expanded={expanded}
    tabIndex={0}
    onKeyPress={(e) => {
      if (e.key === 'Enter' || e.key === ' ') {
        toggleExpanded();
      }
    }}
  >
    View Agent Reasoning
  </summary>
</details>
```

## Performance Considerations

1. **Lazy rendering**: Only render detailed steps when expanded
2. **Virtualization**: For queries with many steps, use virtual scrolling
3. **Memoization**: Memoize expensive rendering operations

```tsx
const AgentStepsTimeline = memo(({ steps }: { steps: ReasoningStep[] }) => {
  // Component implementation
});
```

## User Preferences

Allow users to set their default view:

```tsx
interface UserPreferences {
  showReasoningByDefault: boolean;
  showTechnicalDetails: boolean;
  compactView: boolean;
}

function savePreference(key: string, value: boolean) {
  localStorage.setItem(`agent_ui_${key}`, JSON.stringify(value));
}
```

## Testing

Test the UI with different response types:

```tsx
// Test case 1: Simple query (1 step)
const simpleResponse = {
  reasoning_steps: [
    { step: 1, type: 'final_answer', description: 'Direct answer' }
  ],
  routes_used: { llm_calls: 1, rag_searches: 0, log_queries: 0 }
};

// Test case 2: Complex query (multiple tools)
const complexResponse = {
  reasoning_steps: [
    { step: 1, type: 'tool_call', tool_name: 'query_logs' },
    { step: 2, type: 'tool_call', tool_name: 'search_rag' },
    { step: 3, type: 'final_answer' }
  ],
  routes_used: { llm_calls: 3, rag_searches: 1, log_queries: 1 }
};

// Test case 3: Max iterations
const maxIterResponse = {
  reasoning_steps: [...],
  max_iterations_reached: true
};
```

## Summary

The enhanced agent transparency features enable you to build trust with users by:
- **Showing the work** - Users see exactly what the agent did
- **Explaining decisions** - Clear descriptions of each step
- **Tracking usage** - Users know which tools/capabilities were used
- **Debugging support** - Easy to identify where things went wrong

This creates a more transparent, trustworthy, and debuggable AI assistant!
