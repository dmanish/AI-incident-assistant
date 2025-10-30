#!/usr/bin/env python3
"""
Integration test to verify enhanced tools are loaded correctly
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

def test_tool_imports():
    """Test that enhanced tools are imported correctly"""
    print("=" * 70)
    print("Testing Enhanced Tools Integration")
    print("=" * 70)

    # Test 1: Import tools from function_calling_agent
    print("\n[Test 1] Importing from function_calling_agent...")
    try:
        from app.agent.function_calling_agent import TOOL_DEFINITIONS
        print(f"  ✓ TOOL_DEFINITIONS imported successfully")
        print(f"  ✓ Found {len(TOOL_DEFINITIONS)} tools")

        tool_names = [t["function"]["name"] for t in TOOL_DEFINITIONS]
        print(f"  ✓ Tools: {tool_names}")

        # Verify we have the enhanced tools
        expected_tools = ["search_authentication_logs", "search_knowledge_base", "search_threat_intelligence"]
        for tool in expected_tools:
            if tool in tool_names:
                print(f"    ✓ {tool} present")
            else:
                print(f"    ✗ {tool} MISSING")
                return False

        # Verify old tool is NOT present
        if "query_failed_logins" in tool_names:
            print(f"    ⚠ WARNING: Old tool 'query_failed_logins' still present in TOOL_DEFINITIONS")
        else:
            print(f"    ✓ Old tool 'query_failed_logins' correctly replaced")

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 2: Check executors
    print("\n[Test 2] Checking tool executors...")
    try:
        from app.agent.executors_enhanced import create_enhanced_tool_executors
        print(f"  ✓ create_enhanced_tool_executors imported successfully")

        # Mock functions for testing
        def mock_retrieve(query, role, top_k): return []
        def mock_logs(**kwargs): return []
        def mock_rbac_tool(role, tool): return True
        def mock_rbac_doc(role, doc): return True

        executors = create_enhanced_tool_executors(
            retrieve_chunks_fn=mock_retrieve,
            query_logs_fn=mock_logs,
            role_allows_tool_fn=mock_rbac_tool,
            role_allows_doc_fn=mock_rbac_doc
        )

        print(f"  ✓ Executors created successfully")
        print(f"  ✓ Available executors: {list(executors.keys())}")

        # Verify executors match tool definitions
        for tool_name in expected_tools:
            if tool_name in executors:
                print(f"    ✓ {tool_name} executor present")
            else:
                print(f"    ✗ {tool_name} executor MISSING")
                return False

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test 3: Verify threat intelligence tool description
    print("\n[Test 3] Verifying threat intelligence tool...")
    try:
        threat_intel_tool = None
        for tool in TOOL_DEFINITIONS:
            if tool["function"]["name"] == "search_threat_intelligence":
                threat_intel_tool = tool
                break

        if not threat_intel_tool:
            print("  ✗ FAILED: Threat intelligence tool not found")
            return False

        desc = threat_intel_tool["function"]["description"]
        print(f"  ✓ Threat intelligence tool found")
        print(f"  ✓ Description: {desc[:100]}...")

        # Check if CVE is mentioned in description
        if "CVE" in desc or "cve" in desc.lower():
            print(f"  ✓ CVE capability mentioned in description")
        else:
            print(f"  ⚠ WARNING: CVE not mentioned in tool description")

        # Check parameters
        params = threat_intel_tool["function"]["parameters"]["properties"]
        if "search_type" in params:
            search_types = params["search_type"].get("enum", [])
            print(f"  ✓ search_type parameter with options: {search_types}")
            if "cve" in search_types:
                print(f"    ✓ 'cve' search type available")
            else:
                print(f"    ✗ 'cve' search type MISSING")
                return False
        else:
            print(f"  ✗ search_type parameter MISSING")
            return False

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

    print("\n" + "=" * 70)
    print("✓ All integration tests passed!")
    print("=" * 70)
    print("\nThe agent now has access to:")
    print("  1. search_authentication_logs - Enhanced log search with date ranges, filters, aggregation")
    print("  2. search_knowledge_base - Internal policy/playbook search")
    print("  3. search_threat_intelligence - CVE lookups, IP reputation, threat intel")
    print("\nQueries like 'is there a CVE on TLS' will now use the threat intelligence tool")
    print("instead of incorrectly searching authentication logs!")
    print("=" * 70)

    return True

if __name__ == "__main__":
    success = test_tool_imports()
    sys.exit(0 if success else 1)
