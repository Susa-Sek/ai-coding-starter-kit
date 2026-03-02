#!/usr/bin/env python3
"""
Unified Agent Test Script

Tests the complete Google Business Agent workflow with mock browser.
Run this to verify the agent works correctly before using with a real browser.

Usage:
    python scripts/test_unified_agent.py
"""

import sys
import os
from unittest.mock import Mock, MagicMock

# Add scripts to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))


def test_strategy_loading():
    """Test that all strategies load correctly."""
    print("\n📋 Testing strategy loading...")
    from agents.plugin_manager import PluginManager
    from core.plugin_base import PluginType

    manager = PluginManager()
    manager.load_plugins()

    strategies = manager.get_plugins(PluginType.STRATEGY)
    print(f"   ✓ Loaded {len(strategies)} strategies")

    for s in strategies:
        print(f"     - {s.metadata.name} (priority: {s.metadata.priority}, confidence: {s.confidence_score:.2f})")

    assert len(strategies) >= 1, "At least one strategy should be loaded"
    return True


def test_rule_based_strategy():
    """Test rule-based strategy decision making."""
    print("\n📋 Testing rule-based strategy...")
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Test Google login detection
    login_state = {
        "url": "https://accounts.google.com/signin",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
        "has_email_field": True,
        "has_password_field": False
    }

    analyzed = strategy.analyze_state(login_state)
    action = strategy.decide_action({"goal": "perform_login"}, analyzed, [])

    print(f"   ✓ Analyzed login state: {analyzed['url']}")
    print(f"   ✓ Decided action: {action['type']} (confidence: {action.get('confidence', 0):.2f})")
    assert action["type"] in ["fill_input", "click_button", "wait"]

    # Test dashboard detection (completion)
    dashboard_state = {
        "url": "https://business.google.com/dashboard",
        "text": "Your locations",
        "inputs": [],
        "buttons": [],
        "has_email_field": False,
        "has_password_field": False
    }

    analyzed = strategy.analyze_state(dashboard_state)
    action = strategy.decide_action({"goal": "create_profile"}, analyzed, [])

    print(f"   ✓ Dashboard detection: {action['type']}")
    assert action["type"] == "done"
    return True


def test_hybrid_strategy():
    """Test hybrid strategy combination."""
    print("\n📋 Testing hybrid strategy...")
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    print(f"   ✓ Loaded {len(strategy.strategies)} sub-strategies")
    for s in strategy.strategies:
        print(f"     - {s['type']} (weight: {s['weight']:.2f})")

    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [],
        "buttons": []
    }

    analyzed = strategy.analyze_state(browser_state)
    print(f"   ✓ Analyzed state with {analyzed['strategy_count']} strategies")

    action = strategy.decide_action({"goal": "login"}, analyzed, [])
    print(f"   ✓ Decided action: {action['type']} (via {action.get('reasoning', 'unknown')})")

    return True


def test_agent_initialization():
    """Test agent initialization."""
    print("\n📋 Testing agent initialization...")
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Create a Google Business Profile")

    print(f"   ✓ Task: {agent.task.description}")
    print(f"   ✓ Goal: {agent.task.goal}")
    print(f"   ✓ Strategies loaded: {len(agent.plugin_manager.get_plugins())}")
    print(f"   ✓ Max iterations: {agent.max_iterations}")

    return True


def test_strategy_selection():
    """Test strategy selection."""
    print("\n📋 Testing strategy selection...")
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Login to Google")

    # Test Google URL (should select rule-based)
    google_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [],
        "buttons": []
    }

    strategy = agent._select_strategy(google_state)
    if strategy:
        print(f"   ✓ Selected strategy: {strategy.metadata.name}")
        print(f"   ✓ Confidence: {strategy.confidence_score:.2f}")
    else:
        print("   ⚠ No strategy selected (may need configuration)")

    return True


def test_browser_state_collection():
    """Test browser state collection."""
    print("\n📋 Testing browser state collection...")
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test")

    # Mock browser
    mock_page = Mock()
    mock_page.url = "https://business.google.com/create"
    mock_page.title.return_value = "Create Business Profile"

    body_locator = Mock()
    body_locator.count.return_value = 1
    body_locator.inner_text.return_value = "Business Name Category"
    body_locator.all.return_value = []

    input_locator = Mock()
    input_locator.all.return_value = []

    button_locator = Mock()
    button_locator.all.return_value = []

    def mock_locator(selector):
        if 'body' in selector:
            return body_locator
        elif 'input' in selector:
            return input_locator
        elif 'button' in selector:
            return button_locator
        return Mock(all=lambda: [])

    mock_page.locator = mock_locator

    agent.browser = Mock()
    agent.browser.page = mock_page

    state = agent._get_browser_state()

    print(f"   ✓ URL: {state['url']}")
    print(f"   ✓ Title: {state['title']}")
    print(f"   ✓ Text length: {len(state.get('text', ''))}")

    assert state["url"] == "https://business.google.com/create"
    return True


def test_strategy_execution():
    """Test strategy execution."""
    print("\n📋 Testing strategy execution...")
    from agents.new_ai_agent import NewAIAgent
    from agents.strategies.rule_based import RuleBasedStrategy

    agent = NewAIAgent("Test")
    strategy = RuleBasedStrategy()

    # Mock page
    mock_page = Mock()
    mock_page.keyboard = Mock()
    mock_page.keyboard.press = Mock()

    task = {"description": "Test", "goal": "test"}
    browser_state = {
        "url": "https://business.google.com/dashboard",
        "text": "Dashboard",
        "inputs": [],
        "buttons": [],
        "has_email_field": False,
        "has_password_field": False
    }

    result = agent._execute_with_strategy(strategy, task, browser_state, [])

    print(f"   ✓ Action: {result['action']['type']}")
    print(f"   ✓ Strategy: {result['strategy']}")
    print(f"   ✓ Confidence: {result['confidence']:.2f}")

    assert "action" in result
    assert "result" in result
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("=" * 60)
    print("🧪 Unified Agent Test Suite")
    print("=" * 60)

    tests = [
        ("Strategy Loading", test_strategy_loading),
        ("Rule-Based Strategy", test_rule_based_strategy),
        ("Hybrid Strategy", test_hybrid_strategy),
        ("Agent Initialization", test_agent_initialization),
        ("Strategy Selection", test_strategy_selection),
        ("Browser State Collection", test_browser_state_collection),
        ("Strategy Execution", test_strategy_execution),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            test_func()
            passed += 1
            print(f"   ✅ {name} PASSED")
        except Exception as e:
            failed += 1
            print(f"   ❌ {name} FAILED: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)