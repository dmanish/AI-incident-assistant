#!/usr/bin/env python3
"""
Quick structure validation test (no dependencies required)
Tests that tool definitions are properly formatted
"""

import sys
import json
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.agent.tools_enhanced import TOOL_DEFINITIONS, get_tool_by_name


def test_tool_definitions_structure():
    """Validate tool definition structure"""
    print("Testing tool definitions structure...")

    required_fields = ["type", "function"]
    function_fields = ["name", "description", "parameters"]

    for i, tool in enumerate(TOOL_DEFINITIONS, 1):
        print(f"\n{i}. Validating tool...")

        # Check top-level fields
        for field in required_fields:
            assert field in tool, f"Missing '{field}' in tool definition"

        # Check function fields
        func = tool["function"]
        for field in function_fields:
            assert field in func, f"Missing '{field}' in function definition"

        # Check parameters structure
        params = func["parameters"]
        assert params["type"] == "object", "Parameters must be an object"
        assert "properties" in params, "Parameters must have properties"

        name = func["name"]
        desc = func["description"]
        props = params["properties"]

        print(f"   ✓ {name}")
        print(f"     Description: {desc[:60]}...")
        print(f"     Parameters: {list(props.keys())}")

    print(f"\n✓ All {len(TOOL_DEFINITIONS)} tool definitions are valid")


def test_tool_retrieval():
    """Test get_tool_by_name function"""
    print("\nTesting tool retrieval...")

    tools = ["search_authentication_logs", "search_knowledge_base", "search_threat_intelligence"]

    for tool_name in tools:
        tool = get_tool_by_name(tool_name)
        assert tool is not None, f"Failed to retrieve {tool_name}"
        assert tool["function"]["name"] == tool_name
        print(f"   ✓ {tool_name} retrieved successfully")

    print("✓ Tool retrieval works")


def test_enhanced_vs_original():
    """Compare enhanced vs original tools"""
    print("\nComparing enhanced vs original tools...")

    try:
        from app.agent.tools import TOOL_DEFINITIONS as ORIGINAL_TOOLS

        print(f"   Original tools: {len(ORIGINAL_TOOLS)}")
        print(f"   Enhanced tools: {len(TOOL_DEFINITIONS)}")

        orig_names = {t["function"]["name"] for t in ORIGINAL_TOOLS}
        enhanced_names = {t["function"]["name"] for t in TOOL_DEFINITIONS}

        print(f"\n   Original tool names: {orig_names}")
        print(f"   Enhanced tool names: {enhanced_names}")

        new_tools = enhanced_names - orig_names
        if new_tools:
            print(f"\n   ✓ New tools added: {new_tools}")

        replaced_tools = orig_names - enhanced_names
        if replaced_tools:
            print(f"   ℹ Tools replaced/renamed: {replaced_tools}")

    except ImportError:
        print("   ℹ Original tools.py not found (expected if starting fresh)")


def test_parameter_enhancements():
    """Check that enhanced parameters are present"""
    print("\nValidating parameter enhancements...")

    # Check search_authentication_logs has enhanced parameters
    tool = get_tool_by_name("search_authentication_logs")
    params = tool["function"]["parameters"]["properties"]

    expected_params = [
        "date_start",
        "date_end",
        "result_filter",
        "username",
        "ip_address",
        "aggregate_by"
    ]

    for param in expected_params:
        if param in params:
            print(f"   ✓ {param}: {params[param].get('description', '')[:50]}...")
        else:
            print(f"   ✗ {param}: MISSING")

    # Check threat intelligence tool
    tool = get_tool_by_name("search_threat_intelligence")
    params = tool["function"]["parameters"]["properties"]

    assert "query" in params, "Threat intel tool missing 'query' parameter"
    assert "search_type" in params, "Threat intel tool missing 'search_type' parameter"

    print(f"\n   ✓ Threat intelligence tool has required parameters")


def main():
    """Run all structure tests"""
    print("=" * 70)
    print("  TOOL STRUCTURE VALIDATION")
    print("=" * 70)

    tests = [
        test_tool_definitions_structure,
        test_tool_retrieval,
        test_enhanced_vs_original,
        test_parameter_enhancements
    ]

    passed = 0
    failed = 0

    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n✗ TEST FAILED: {test_func.__name__}")
            print(f"  Error: {str(e)}")
            failed += 1
        except Exception as e:
            print(f"\n✗ TEST ERROR: {test_func.__name__}")
            print(f"  Error: {str(e)}")
            failed += 1

    # Summary
    print("\n" + "=" * 70)
    print(f"  VALIDATION SUMMARY")
    print("=" * 70)
    print(f"  Total tests: {passed + failed}")
    print(f"  ✓ Passed: {passed}")
    print(f"  ✗ Failed: {failed}")
    print("=" * 70 + "\n")

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
