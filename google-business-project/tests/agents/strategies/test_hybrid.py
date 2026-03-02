#!/usr/bin/env python3
"""
Tests for Hybrid Strategy Plugin.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))


def test_hybrid_strategy_creation():
    """Test hybrid strategy plugin creation"""
    from agents.strategies.hybrid import HybridStrategy
    from core.plugin_base import PluginType

    strategy = HybridStrategy()

    assert strategy.metadata.name == "HybridStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert hasattr(strategy, 'confidence_score')
    assert hasattr(strategy, 'strategies')
    assert strategy.metadata.priority == 20  # High priority


def test_hybrid_has_sub_strategies():
    """Test that hybrid strategy has sub-strategies"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    # Should have at least one strategy (rule-based doesn't need external deps)
    assert len(strategy.strategies) >= 1


def test_hybrid_analyze_state():
    """Test that hybrid strategy analyzes state through sub-strategies"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [],
        "buttons": []
    }

    analyzed = strategy.analyze_state(browser_state)

    assert "url" in analyzed
    assert "strategy_count" in analyzed
    assert analyzed["strategy_count"] >= 1


def test_hybrid_decide_action_no_strategies():
    """Test decision when no sub-strategies can handle"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    # Force empty strategies for test
    original_strategies = strategy.strategies
    strategy.strategies = []

    task = {"description": "Test", "goal": "test"}
    state = {"url": "https://example.com", "text": "", "inputs_count": 0, "buttons_count": 0}
    action = strategy.decide_action(task, state, [])

    # Should return low-confidence wait action
    assert action["type"] == "wait"
    assert action["confidence"] <= 0.2

    # Restore
    strategy.strategies = original_strategies


def test_hybrid_can_handle():
    """Test can_handle method"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    # Should handle Google URLs (via rule-based)
    google_state = {"url": "https://accounts.google.com", "text": "Email"}
    assert strategy.can_handle(google_state) == True


def test_hybrid_execute_action_wait():
    """Test executing wait action"""
    from agents.strategies.hybrid import HybridStrategy
    from unittest.mock import Mock

    strategy = HybridStrategy()

    # Test wait action (fallback)
    action = {"type": "wait", "details": {"seconds": 1}}
    result = strategy.execute_action(action, Mock())

    assert result["success"] == True


def test_hybrid_confidence_score():
    """Test confidence score calculation"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    score = strategy.confidence_score

    assert 0.0 <= score <= 1.0
    # Should have some confidence from sub-strategies
    assert score > 0.0


def test_hybrid_uses_best_strategy():
    """Test that hybrid selects best strategy based on confidence"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    # Google URL should be handled by rule-based strategy
    google_state = {
        "url": "https://accounts.google.com/signin",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
        "has_email_field": True,
        "has_password_field": False
    }

    task = {"description": "Login", "goal": "perform_login"}
    action = strategy.decide_action(task, google_state, [])

    # Should get a valid action
    assert "type" in action
    assert "reasoning" in action


if __name__ == "__main__":
    pytest.main([__file__, "-v"])