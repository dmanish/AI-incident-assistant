# Documentation

## Interactive Query Flow Diagram

An interactive HTML visualization of the end-to-end query flow with clickable links to code.

### View the Diagram

Open in your web browser:

```bash
# macOS
open docs/query_flow_diagram.html

# Linux
xdg-open docs/query_flow_diagram.html

# Or manually open in browser
# File path: /Users/manish/Projects/EOS_cyber/AI-incident-assistant/docs/query_flow_diagram.html
```

### Features

- **Interactive Flow:** Visual representation of all 10 steps in query processing
- **Clickable Links:** Each box has links to specific code files and line numbers
- **Color-Coded:** Different colors for different components (UI, API, Routing, Tools, etc.)
- **Performance Metrics:** Real-time performance data for each stage
- **NEW: Learning Loop:** Visualization of the continuous learning system

### Sections

1. **User Input** - React UI components
2. **API Gateway** - FastAPI endpoints, JWT validation
3. **Agent Selection** - Heuristic vs Function Calling
4. **Semantic Routing** - 3-tier routing system
5. **Tool Execution** - RAG, Logs, Web Search (parallel)
6. **LLM Synthesis** - Multi-provider response generation
7. **DLP Filtering** - Data loss prevention
8. **Audit Logging** - Compliance logging
9. **Response** - User-facing output
10. **🎓 Continuous Learning** - NEW! Feedback-based improvement

### Code Navigation

Click on any "📄 filename.py" link in the diagram to jump to that file in your editor. Links are relative paths from the project root.

### Print/Export

The diagram is print-friendly. Use your browser's print function (Cmd+P / Ctrl+P) to create a PDF version.

---

For detailed documentation on the Continuous Learning System, see:
- [CONTINUOUS_LEARNING_SYSTEM.md](./CONTINUOUS_LEARNING_SYSTEM.md)
