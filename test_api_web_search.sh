#!/bin/bash
# Test web search through the API
set -e

echo "======================================================================"
echo "Testing Web Search Through Docker API"
echo "======================================================================"

# Step 1: Login
echo ""
echo "Step 1: Logging in..."
TOKEN=$(curl -s -X POST http://localhost:8080/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"alice@company","password":"password"}' | \
  python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('token', ''))" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo "✗ Login failed. Trying bob@company..."
  TOKEN=$(curl -s -X POST http://localhost:8080/login \
    -H 'Content-Type: application/json' \
    -d '{"email":"bob@company","password":"password"}' | \
    python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('token', ''))" 2>/dev/null)
fi

if [ -z "$TOKEN" ]; then
  echo "✗ Login failed with both users. Please check credentials."
  exit 1
fi

echo "✓ Logged in successfully"

# Step 2: Test CVE query
echo ""
echo "Step 2: Testing CVE query..."
echo "Query: 'is there a CVE on TLS'"
echo ""

RESPONSE=$(curl -s -X POST http://localhost:8080/agent/chat \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"message":"is there a CVE on TLS"}')

echo "Response:"
echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"

echo ""
echo "----------------------------------------------------------------------"
echo "Step 3: Check audit log for web search"
echo "----------------------------------------------------------------------"

echo "Recent web search decisions:"
tail -50 data/logs/audit.log | grep "web_search" | tail -5

echo ""
echo "======================================================================"
echo "Test Complete"
echo "======================================================================"
echo ""
echo "If the response above is blank or doesn't contain CVE information,"
echo "please share the output with me so I can debug further."
