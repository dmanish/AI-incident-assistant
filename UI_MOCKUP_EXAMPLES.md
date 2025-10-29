# UI Mockups for Agent Transparency

## Example 1: Simple Query Response

**User:** "Show me failed logins"

### Response UI

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI Assistant                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ I found 15 failed login attempts in today's authentication     │
│ logs. Here are the details:                                    │
│                                                                 │
│ • 10 attempts from user alice (IP: 192.168.1.100)             │
│ • 3 attempts from user bob (IP: 10.0.0.50)                    │
│ • 2 attempts from user charlie (IP: 192.168.1.101)            │
│                                                                 │
│ All attempts occurred between 2:00 AM - 2:15 AM UTC.          │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ 🎯 Routes Used                                            │ │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │
│ │ 🤖 LLM (2 calls)  │  📊 Logs (1 query)                   │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─ 🔍 View Agent Reasoning (1 step) ▼─────────────────────┐   │
│ │                                                          │   │
│ │ Step 1: 🔧 Tool Call                                     │   │
│ │ ├─ Queried authentication logs for failed login         │   │
│ │ │  attempts                                              │   │
│ │ ├─ Parameters:                                           │   │
│ │ │  • date: "2025-10-28"                                  │   │
│ │ │  • limit: 200                                          │   │
│ │ └─ ✓ Success: Found 15 results                           │   │
│ │                                                          │   │
│ │ Step 2: 🧠 Final Answer                                   │   │
│ │ └─ Agent synthesized response from log data             │   │
│ │                                                          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ 📊 Technical Details ▶──────────────────────────────────┐   │
│ │ (Click to expand)                                        │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 2: Complex Multi-Step Query

**User:** "What should I do about failed logins for jdoe? Check the logs and tell me the policy."

### Response UI

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI Assistant                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ I found 50 failed login attempts for user jdoe today. Based on │
│ our Account Security Policy, here's what you should do:        │
│                                                                 │
│ **Immediate Actions:**                                          │
│ 1. Lock jdoe's account temporarily                             │
│ 2. Contact jdoe to verify if this was legitimate activity      │
│ 3. Review IP 192.168.1.100 for known threats                   │
│ 4. Enable MFA if not already active                            │
│                                                                 │
│ **Investigation Steps:**                                        │
│ • All 50 attempts came from IP 192.168.1.100                   │
│ • Attempts occurred in a 15-minute window (2:00-2:15 AM)       │
│ • Pattern suggests automated attack                            │
│                                                                 │
│ **Policy Reference:**                                           │
│ According to our Account Security Response Playbook:           │
│ - Lock account after 5 failed attempts ✓                       │
│ - Notify user via email ⚠️ Pending                             │
│ - Review IP for known threats ⚠️ Pending                       │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ 🎯 Routes Used                                            │ │
│ │ ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │ │
│ │ 🤖 LLM (3 calls) │ 📚 RAG (1 search) │ 📊 Logs (1 query) │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─ 🔍 View Agent Reasoning (3 steps) ▼─────────────────────┐   │
│ │                                                          │   │
│ │ Step 1: 🔧 Query Logs                                     │   │
│ │ ├─ Queried authentication logs for failed login         │   │
│ │ │  attempts                                              │   │
│ │ ├─ Parameters:                                           │   │
│ │ │  • date: "2025-10-28"                                  │   │
│ │ │  • username: "jdoe"                                    │   │
│ │ │  • limit: 200                                          │   │
│ │ └─ ✓ Success: Found 50 failed login attempts from       │   │
│ │    IP 192.168.1.100                                      │   │
│ │                                                          │   │
│ │ Step 2: 📚 Search Policy                                  │   │
│ │ ├─ Searched security policies and playbooks             │   │
│ │ ├─ Query: "failed login security policy response"       │   │
│ │ └─ ✓ Success: Found Account Security Response Playbook  │   │
│ │                                                          │   │
│ │ Step 3: 🧠 Final Answer                                   │   │
│ │ └─ Agent synthesized response combining log data and    │   │
│ │    policy guidance                                       │   │
│ │                                                          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
│ ┌─ 📊 Technical Details ▼──────────────────────────────────┐   │
│ │ Model: gpt-4o-mini                                       │   │
│ │ Iterations: 3                                            │   │
│ │ LLM Calls: 3                                             │   │
│ │ Tools Used: query_failed_logins, search_knowledge_base  │   │
│ │                                                          │   │
│ │ Capabilities:                                            │   │
│ │ [✓ RAG]  [✓ Log Query]                                  │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 3: Compact Mobile View

```
┌──────────────────────────────┐
│ 🤖 AI Assistant              │
├──────────────────────────────┤
│                              │
│ I found 50 failed login      │
│ attempts for jdoe. Here's    │
│ what to do:                  │
│                              │
│ 1. Lock account temporarily  │
│ 2. Contact user jdoe         │
│ 3. Review IP for threats     │
│ 4. Enable MFA                │
│                              │
│ ┌──────────────────────────┐ │
│ │ 🎯 Quick Stats           │ │
│ │ 3 LLM calls • 2 tools    │ │
│ │ Used: RAG, Logs          │ │
│ └──────────────────────────┘ │
│                              │
│ [View Reasoning Steps ▼]     │
│                              │
└──────────────────────────────┘
```

---

## Example 4: Error State

**When a tool fails or RBAC denies access:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI Assistant                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ ⚠️ I encountered an issue while processing your request.        │
│                                                                 │
│ I was unable to query the authentication logs because your     │
│ role (sales) does not have permission to access log data.      │
│                                                                 │
│ However, I can still help with policy questions or general     │
│ security guidance.                                             │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ 🎯 Routes Used                                            │ │
│ │ 🤖 LLM (1 call)  │  ❌ Logs (blocked by RBAC)            │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ ┌─ 🔍 View Agent Reasoning (2 steps) ▼─────────────────────┐   │
│ │                                                          │   │
│ │ Step 1: 🔧 Attempted Tool Call                            │   │
│ │ ├─ Tried to query authentication logs                    │   │
│ │ ├─ Parameters: date="2025-10-28"                         │   │
│ │ └─ ✗ Failed: Permission denied for role 'sales'          │   │
│ │                                                          │   │
│ │ Step 2: 🧠 Error Response                                 │   │
│ │ └─ Agent explained the permission issue and offered     │   │
│ │    alternative assistance                                │   │
│ │                                                          │   │
│ └──────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 5: Progress Indicator (Real-time)

**While agent is thinking:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 🤖 AI Assistant                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ 🔄 Thinking...                                                  │
│                                                                 │
│ ┌───────────────────────────────────────────────────────────┐ │
│ │ Iteration 2 of 5                                          │ │
│ │ ████████░░░░░░░░░░░░░░  40%                                │ │
│ └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│ Current Step:                                                   │
│ • Querying authentication logs...  ✓                           │
│ • Synthesizing response... ⏳                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 6: Comparison View (A/B Testing)

**Show difference between simple workflow and agent:**

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 Agent Mode: Function Calling ▼ [Switch to Simple Mode]      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ [Agent response here...]                                        │
│                                                                 │
│ ┌─ ℹ️ How this differs from Simple Mode ──────────────────────┐ │
│ │                                                             │ │
│ │ Simple Mode:                                                │ │
│ │ • Uses keyword matching                                     │ │
│ │ • Single tool call                                          │ │
│ │ • No multi-step reasoning                                   │ │
│ │                                                             │ │
│ │ Agent Mode (Current):                                       │ │
│ │ ✓ LLM decides which tools to use                           │ │
│ │ ✓ Can call multiple tools                                   │ │
│ │ ✓ Iterative reasoning                                       │ │
│ │ ✓ Context-aware decisions                                   │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Example 7: Debug View (For Developers)

```
┌─────────────────────────────────────────────────────────────────┐
│ 🔧 Debug Mode: ON                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ [Agent response...]                                             │
│                                                                 │
│ ┌─ 🐛 Debug Information ▼──────────────────────────────────────┐ │
│ │                                                             │ │
│ │ Request ID: abc123                                          │ │
│ │ Timestamp: 2025-10-28T15:30:45Z                             │ │
│ │ Duration: 3.2s                                              │ │
│ │                                                             │ │
│ │ Token Usage:                                                │ │
│ │ • Input: 1,250 tokens                                       │ │
│ │ • Output: 450 tokens                                        │ │
│ │ • Cost: $0.003                                              │ │
│ │                                                             │ │
│ │ Tool Execution Times:                                       │ │
│ │ • query_failed_logins: 0.8s                                │ │
│ │ • search_knowledge_base: 1.2s                              │ │
│ │ • llm_synthesis: 1.2s                                       │ │
│ │                                                             │ │
│ │ [Copy Raw Response JSON]  [View Audit Log]                 │ │
│ │                                                             │ │
│ └─────────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Color Scheme Suggestions

### Light Mode
```
Background: #FFFFFF
Text: #1a1a1a
Success: #28a745
Error: #dc3545
Warning: #ffc107
Info: #17a2b8
Agent Color: #667eea (purple gradient)
Tool Call: #007bff
Final Answer: #6c757d
```

### Dark Mode
```
Background: #1a1a1a
Text: #e0e0e0
Success: #4caf50
Error: #f44336
Warning: #ff9800
Info: #03a9f4
Agent Color: #9c27b0
Tool Call: #2196f3
Final Answer: #90a4ae
```

---

## Animation Ideas

1. **Step Reveal**: Fade in each reasoning step as it's completed
2. **Progress Bar**: Smooth animation showing iteration progress
3. **Tool Icon Pulse**: Pulse animation when tool is being executed
4. **Success Check**: Checkmark animation when step succeeds
5. **Expand/Collapse**: Smooth height transition for expandable sections

---

## Accessibility Features

- **Screen Reader**: Announce when agent completes a step
- **Keyboard Navigation**: Tab through all interactive elements
- **Focus Indicators**: Clear visual feedback
- **High Contrast**: All text meets WCAG AA standards
- **Reduced Motion**: Respect prefers-reduced-motion

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

These mockups show how to make the agent's reasoning process transparent and user-friendly while maintaining a clean, professional interface!
