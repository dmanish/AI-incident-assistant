# Continuous Learning System for Routing

## Overview

The AI Incident Assistant now includes a **Continuous Learning System** that improves routing accuracy over time by learning from user feedback. This creates a feedback loop that continuously refines the semantic routing model.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interaction                         │
│  1. User submits query                                       │
│  2. System routes to tools                                   │
│  3. User provides feedback (correct/incorrect/partial)       │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Feedback Collection                         │
│  • Store in routing_metrics.db                              │
│  • Record actual vs expected routing                        │
│  • Track confidence scores                                  │
│  • Capture user comments                                    │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                   Pattern Analysis                           │
│  • Weekly/on-demand analysis                                │
│  • Identify recurring incorrect routing                     │
│  • Cluster similar queries                                  │
│  • Calculate pattern confidence                             │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Training Example Generation                     │
│  • Auto-generate examples from patterns                     │
│  • Auto-approve high-confidence patterns (5+ occurrences)   │
│  • Export for admin review                                  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│               Model Improvement                              │
│  • Admin reviews and approves examples                      │
│  • Add to seed_examples.json                                │
│  • Re-ingest to rebuild routing vector DB                   │
│  • Improved accuracy for future queries                     │
└─────────────────────────────────────────────────────────────┘
```

## Key Features

### 1. Feedback Collection

**API Endpoint:** `POST /agent/routing/feedback`

Users can provide feedback on routing decisions:

```json
{
  "query": "show me authentication logs",
  "actual_route": {
    "use_rag": true,
    "use_logs": false,
    "use_web_search": false
  },
  "expected_route": {
    "use_rag": false,
    "use_logs": true,
    "use_web_search": false
  },
  "feedback_type": "incorrect",
  "confidence_score": 0.65,
  "routing_method": "semantic",
  "user_comment": "Should have used logs, not RAG"
}
```

**Feedback Types:**
- `correct` - Routing was correct
- `incorrect` - Routing was wrong
- `partial` - Routing was partially correct

### 2. Pattern Analysis

**API Endpoint:** `GET /agent/routing/feedback/stats`

Provides statistics on routing accuracy:

```json
{
  "period_days": 30,
  "total_feedback": 150,
  "feedback_breakdown": {
    "correct": 135,
    "incorrect": 12,
    "partial": 3
  },
  "accuracy_rate": 90.0,
  "unprocessed_patterns": 5,
  "can_generate_examples": true
}
```

### 3. Automatic Learning

**API Endpoint:** `POST /agent/routing/learn` (Admin only)

Triggers the learning process:

1. **Analyze Feedback:** Find queries with consistent incorrect routing
2. **Generate Examples:** Auto-create training examples from patterns
3. **Auto-Approve:** Examples with 5+ occurrences are auto-approved
4. **Export for Review:** Admin reviews generated examples
5. **Ingest:** Approved examples rebuild routing vector database

### 4. Database Schema

**Table:** `routing_feedback`

```sql
CREATE TABLE routing_feedback (
    id INTEGER PRIMARY KEY,
    query TEXT NOT NULL,
    actual_route TEXT NOT NULL,      -- JSON
    expected_route TEXT,              -- JSON
    feedback_type TEXT NOT NULL,      -- correct|incorrect|partial
    user_id TEXT,
    session_id TEXT,
    confidence_score REAL,
    routing_method TEXT,              -- override|semantic|fallback
    user_comment TEXT,
    timestamp TEXT,
    processed INTEGER DEFAULT 0,      -- Whether incorporated
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### For End Users

**1. Submit Feedback (Frontend Integration)**

```typescript
// In React component
const submitFeedback = async (isCorrect: boolean) => {
  await fetch('/agent/routing/feedback', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      query: userQuery,
      actual_route: routingDecision,
      feedback_type: isCorrect ? 'correct' : 'incorrect',
      expected_route: isCorrect ? null : userExpectedRoute,
      confidence_score: routingDecision.confidence,
      routing_method: routingDecision.method
    })
  });
};
```

**2. View Accuracy Stats**

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8080/agent/routing/feedback/stats?days=30
```

### For Administrators

**1. Trigger Learning Process**

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  http://localhost:8080/agent/routing/learn
```

**2. Review Generated Examples**

```bash
cat data/routing/feedback_training_examples.json
```

**3. Approve and Ingest**

```bash
# Review and merge approved examples
cat data/routing/feedback_training_examples.json >> data/routing/seed_examples.json

# Rebuild routing database
python scripts/ingest_routing_examples.py
```

## Workflow

### Weekly Learning Cycle

**Monday:** Users interact with system, provide feedback
```
Week 1 Activity:
- 1000 queries processed
- 950 correct routes (95% accuracy)
- 50 incorrect routes flagged
- Patterns identified: 3 recurring issues
```

**Friday:** Admin triggers learning

```bash
# Step 1: Analyze patterns
curl -X POST http://localhost:8080/agent/routing/learn

# Step 2: Review examples
cat data/routing/feedback_training_examples.json

# Step 3: Approve good examples
# Manually review and merge to seed_examples.json

# Step 4: Re-ingest
python scripts/ingest_routing_examples.py
```

**Next Week:** Improved accuracy
```
Week 2 Activity:
- 1000 queries processed
- 980 correct routes (98% accuracy) ⬆️ +3%
- 20 incorrect routes (down from 50)
- Continuous improvement!
```

## Benefits

### 1. Continuous Improvement
- System learns from real-world usage
- Accuracy improves over time
- Adapts to organization-specific queries

### 2. Low Maintenance
- Auto-generates training examples
- Auto-approves high-confidence patterns
- Minimal manual intervention required

### 3. Transparent
- Full audit trail of feedback
- Explainable improvements
- Statistics dashboard

### 4. Safe
- Admin review before ingestion
- Rollback capability (Git-versioned seed data)
- No automatic deployment without approval

## Integration Points

### 1. Frontend (React)

Add feedback buttons to the UI:

```tsx
// In ChatPane.tsx or ReasoningPane.tsx
<div className="routing-feedback">
  <p>Was this routing correct?</p>
  <button onClick={() => handleFeedback('correct')}>
    ✅ Correct
  </button>
  <button onClick={() => handleFeedback('incorrect')}>
    ❌ Incorrect
  </button>
</div>
```

### 2. Backend API

Already integrated at:
- `app/main.py:785` - POST /agent/routing/feedback
- `app/main.py:837` - GET /agent/routing/feedback/stats
- `app/main.py:857` - POST /agent/routing/learn

### 3. Routing System

Feedback manager available via:
```python
from app.agent.routing_feedback import get_feedback_manager

feedback_mgr = get_feedback_manager()
```

## Configuration

### Thresholds

```python
# In routing_feedback.py
AUTO_APPROVE_THRESHOLD = 5  # Auto-approve with 5+ occurrences
MIN_OCCURRENCES = 3         # Min times pattern must occur
LOOKBACK_DAYS = 30          # Analysis window
```

### Adjust in Code

```python
# Custom thresholds
patterns = feedback_mgr.analyze_feedback_patterns(
    days=14,              # Last 2 weeks
    min_occurrences=2     # Lower threshold
)

examples = feedback_mgr.generate_training_examples(
    patterns=patterns,
    auto_approve_threshold=10  # Higher threshold
)
```

## Monitoring

### Key Metrics to Track

1. **Accuracy Rate:** % of correct routing decisions
2. **Feedback Volume:** Total feedback submissions
3. **Improvement Rate:** Accuracy increase over time
4. **Pattern Detection:** Number of recurring issues identified
5. **Example Generation:** Training examples created per cycle

### Dashboard (Future Enhancement)

```
┌───────────────────────────────────────────────────┐
│  Routing Accuracy Dashboard                       │
├───────────────────────────────────────────────────┤
│  Current Accuracy:     95.2% ⬆️ +2.3%            │
│  Total Feedback:       1,247                      │
│  Unprocessed Patterns: 3                          │
│  Last Learning Cycle:  2025-10-29                 │
│                                                   │
│  [Trigger Learning] [View Patterns] [Export]     │
└───────────────────────────────────────────────────┘
```

## Testing

Run the test suite:

```bash
python test_routing_learning.py
```

Output:
```
============================================================
🎓 Testing Routing Learning & Feedback System
============================================================

Test 1: Recording Feedback
✅ Feedback recording complete

Test 2: Analyzing Feedback Patterns
✅ Found 3 patterns

Test 3: Generating Training Examples
✅ Generated 3 training examples

Test 4: Feedback Statistics
✅ Accuracy Rate: 90.0%

============================================================
✅ ALL TESTS PASSED
============================================================
```

## Security Considerations

### Access Control

- **Feedback Submission:** All authenticated users
- **Feedback Stats:** All authenticated users
- **Learning Trigger:** Admin/Security roles only
- **Example Approval:** Manual process (admin only)

### Privacy

- User IDs stored with feedback for audit
- No sensitive query content in examples
- Feedback database isolated from production data

### Safety

- No automatic model updates without admin approval
- All changes version-controlled in Git
- Rollback capability via Git history
- Audit log of all learning cycles

## File Structure

```
AI-incident-assistant/
├── app/agent/
│   ├── routing_feedback.py          # NEW: Feedback manager
│   ├── semantic_router.py            # Routing system
│   └── routing_logger.py             # Analytics logger
│
├── data/routing/
│   ├── routing_metrics.db            # Feedback database
│   ├── feedback_training_examples.json  # NEW: Generated examples
│   └── seed_examples.json            # Training data
│
├── docs/
│   └── query_flow_diagram.html       # NEW: Interactive diagram
│
└── test_routing_learning.py          # NEW: Test suite
```

## Next Steps

1. **Add Frontend UI:** Feedback buttons in React components
2. **Automated Reports:** Weekly email with accuracy stats
3. **Pattern Visualization:** Dashboard for admin review
4. **A/B Testing:** Compare routing models before deployment
5. **Confidence Threshold Tuning:** Dynamic adjustment based on feedback

## Conclusion

The Continuous Learning System enables the AI Incident Assistant to **improve itself over time** by learning from real-world usage. This creates a powerful feedback loop that ensures routing accuracy continuously increases, adapting to your organization's specific needs and query patterns.

**Key Takeaway:** The system doesn't just route queries—it learns from every interaction and gets smarter with use.

---

**Document Version:** 1.0
**Last Updated:** October 2025
**Author:** Manish Dahiya
