#!/usr/bin/env python3
"""
Test the routing learning and feedback system
"""

from app.agent.routing_feedback import get_feedback_manager


def test_feedback_collection():
    """Test feedback recording"""
    print("Test 1: Recording Feedback")
    print("=" * 60)

    feedback_mgr = get_feedback_manager()

    # Simulate some incorrect routing feedback
    test_cases = [
        {
            "query": "how many CVE were reported on glib this year",
            "actual_route": {"use_rag": False, "use_logs": False, "use_web_search": True},
            "expected_route": {"use_rag": False, "use_logs": False, "use_web_search": True},
            "feedback_type": "correct",  # This is actually correct after our fix!
            "confidence_score": 0.85,
            "routing_method": "semantic"
        },
        {
            "query": "show me authentication logs",
            "actual_route": {"use_rag": True, "use_logs": False, "use_web_search": False},
            "expected_route": {"use_rag": False, "use_logs": True, "use_web_search": False},
            "feedback_type": "incorrect",
            "confidence_score": 0.65,
            "routing_method": "semantic",
            "user_comment": "Should have used logs, not RAG"
        },
        {
            "query": "what are the login attempts today",
            "actual_route": {"use_rag": True, "use_logs": False, "use_web_search": False},
            "expected_route": {"use_rag": False, "use_logs": True, "use_web_search": False},
            "feedback_type": "incorrect",
            "confidence_score": 0.62,
            "routing_method": "semantic",
            "user_comment": "Should check logs"
        },
        {
            "query": "authentication logs today",
            "actual_route": {"use_rag": True, "use_logs": False, "use_web_search": False},
            "expected_route": {"use_rag": False, "use_logs": True, "use_web_search": False},
            "feedback_type": "incorrect",
            "confidence_score": 0.68,
            "routing_method": "semantic",
            "user_comment": "Logs please"
        },
    ]

    for i, test_case in enumerate(test_cases, 1):
        feedback_id = feedback_mgr.record_feedback(**test_case)
        print(f"{i}. Recorded feedback ID: {feedback_id}")
        print(f"   Query: {test_case['query']}")
        print(f"   Type: {test_case['feedback_type']}")

    print("\n✅ Feedback recording complete\n")


def test_pattern_analysis():
    """Test pattern analysis"""
    print("Test 2: Analyzing Feedback Patterns")
    print("=" * 60)

    feedback_mgr = get_feedback_manager()

    patterns = feedback_mgr.analyze_feedback_patterns(days=30, min_occurrences=1)

    print(f"Found {len(patterns)} patterns:\n")

    for i, pattern in enumerate(patterns, 1):
        print(f"{i}. Query: {pattern['query']}")
        print(f"   Occurrences: {pattern['occurrences']}")
        print(f"   Avg Confidence: {pattern['avg_confidence']:.2f}")
        print(f"   Priority: {pattern['priority']}")
        print(f"   Actual Route: {pattern['actual_route']}")
        print(f"   Expected Route: {pattern['expected_route']}")
        if pattern.get('user_comments'):
            print(f"   Comments: {pattern['user_comments']}")
        print()

    print("✅ Pattern analysis complete\n")
    return patterns


def test_training_generation(patterns):
    """Test training example generation"""
    print("Test 3: Generating Training Examples")
    print("=" * 60)

    feedback_mgr = get_feedback_manager()

    examples = feedback_mgr.generate_training_examples(patterns)

    print(f"Generated {len(examples)} training examples:\n")

    for i, example in enumerate(examples, 1):
        print(f"{i}. Query: {example['query']}")
        print(f"   Category: {example['category']}")
        print(f"   Route: RAG={example['use_rag']}, Logs={example['use_logs']}, Web={example['use_web_search']}")
        print(f"   Source: {example['source']}")
        print(f"   Auto-approved: {example['auto_approved']}")
        print(f"   Occurrences: {example['occurrences']}")
        print()

    # Export for review
    num_exported = feedback_mgr.export_training_examples()
    print(f"✅ Exported {num_exported} examples to data/routing/feedback_training_examples.json\n")


def test_feedback_stats():
    """Test feedback statistics"""
    print("Test 4: Feedback Statistics")
    print("=" * 60)

    feedback_mgr = get_feedback_manager()

    stats = feedback_mgr.get_feedback_stats(days=30)

    print(f"Period: Last {stats['period_days']} days")
    print(f"Total Feedback: {stats['total_feedback']}")
    print(f"Accuracy Rate: {stats['accuracy_rate']}%")
    print(f"\nFeedback Breakdown:")
    for feedback_type, count in stats['feedback_breakdown'].items():
        print(f"  - {feedback_type}: {count}")
    print(f"\nUnprocessed Patterns: {stats['unprocessed_patterns']}")
    print(f"Can Generate Examples: {stats['can_generate_examples']}")

    print("\n✅ Statistics retrieved\n")


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🎓 Testing Routing Learning & Feedback System")
    print("=" * 60 + "\n")

    try:
        # Test 1: Record feedback
        test_feedback_collection()

        # Test 2: Analyze patterns
        patterns = test_pattern_analysis()

        # Test 3: Generate training examples
        if patterns:
            test_training_generation(patterns)
        else:
            print("⚠️  No patterns found (need min 3 occurrences)\n")

        # Test 4: Get stats
        test_feedback_stats()

        print("=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        print("\nNext Steps:")
        print("1. Review: data/routing/feedback_training_examples.json")
        print("2. Approve examples by adding to: data/routing/seed_examples.json")
        print("3. Re-ingest: python scripts/ingest_routing_examples.py")
        print("4. Improved routing accuracy!")

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
