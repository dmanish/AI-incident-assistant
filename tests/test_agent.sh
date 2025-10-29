#!/usr/bin/env bash
# Test script for the new function calling agent

set -e

API_URL="${API_URL:-http://localhost:8080}"
EMAIL="${EMAIL:-alice@company}"
PASSWORD="${PASSWORD:-pass1}"

echo "🧪 Testing Function Calling Agent"
echo "API URL: $API_URL"
echo ""

# Login
echo "1️⃣  Logging in as $EMAIL..."
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}")

TOKEN=$(echo "$LOGIN_RESPONSE" | jq -r .token)
ROLE=$(echo "$LOGIN_RESPONSE" | jq -r .role)

if [ "$TOKEN" = "null" ]; then
  echo "❌ Login failed!"
  echo "$LOGIN_RESPONSE" | jq .
  exit 1
fi

echo "✅ Logged in successfully"
echo "   Role: $ROLE"
echo "   Token: ${TOKEN:0:20}..."
echo ""

# Test 1: Simple query with tool calling
echo "2️⃣  Test 1: Query failed logins"
echo "   Query: 'Show me failed login attempts from today'"
echo ""

RESPONSE1=$(curl -s -X POST "$API_URL/agent/chat/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me failed login attempts from today"
  }')

echo "Response:"
echo "$RESPONSE1" | jq '{
  reply: .reply[:200],
  iterations: .iterations,
  tool_calls: .tool_calls,
  agent_type: .agent_type
}'
echo ""

# Test 2: Multi-tool query
echo "3️⃣  Test 2: Multi-tool query (policy + logs)"
echo "   Query: 'What should I do about failed logins? Check todays logs too'"
echo ""

RESPONSE2=$(curl -s -X POST "$API_URL/agent/chat/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What should I do about failed logins? Check todays logs too"
  }')

echo "Response:"
echo "$RESPONSE2" | jq '{
  reply: .reply[:300],
  iterations: .iterations,
  tool_calls: .tool_calls | length,
  agent_type: .agent_type
}'
echo ""

# Test 3: Multi-turn conversation
echo "4️⃣  Test 3: Multi-turn conversation"
echo "   Turn 1: 'Show me failed logins'"
echo ""

RESPONSE3=$(curl -s -X POST "$API_URL/agent/chat/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me failed logins"
  }')

CONVO_ID=$(echo "$RESPONSE3" | jq -r .convo_id)
echo "   Conversation ID: $CONVO_ID"
echo "   Reply: $(echo "$RESPONSE3" | jq -r .reply | head -c 100)..."
echo ""

echo "   Turn 2 (follow-up): 'Tell me more about those IPs'"
echo ""

RESPONSE4=$(curl -s -X POST "$API_URL/agent/chat/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"message\": \"Tell me more about those IPs\",
    \"convo_id\": \"$CONVO_ID\"
  }")

echo "Response:"
echo "$RESPONSE4" | jq '{
  reply: .reply[:200],
  iterations: .iterations,
  convo_id: .convo_id
}'
echo ""

# Test 4: Policy search
echo "5️⃣  Test 4: Policy search only"
echo "   Query: 'How should I handle a phishing email?'"
echo ""

RESPONSE5=$(curl -s -X POST "$API_URL/agent/chat/v2" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How should I handle a phishing email?"
  }')

echo "Response:"
echo "$RESPONSE5" | jq '{
  reply: .reply[:300],
  iterations: .iterations,
  tool_calls: .tool_calls,
  agent_type: .agent_type
}'
echo ""

# Memory stats
echo "6️⃣  Memory statistics"
MEMORY_STATS=$(curl -s -X GET "$API_URL/agent/memory/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$MEMORY_STATS" | jq .
echo ""

echo "✅ All tests completed!"
echo ""
echo "💡 Tips:"
echo "   - Check audit logs: tail -f data/logs/audit.log | jq ."
echo "   - Compare with old agent: POST /agent/chat (without /v2)"
echo "   - Try complex multi-step queries to see iterative reasoning"
