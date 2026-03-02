#!/usr/bin/env python3
"""
Tests for AI-Driven Strategy Plugin.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))


def test_ai_driven_strategy_creation():
    """Test AI-driven strategy plugin creation"""
    from agents.strategies.ai_driven import AIDrivenStrategy
    from core.plugin_base import PluginType

    strategy = AIDrivenStrategy()

    assert strategy.metadata.name == "AIDrivenStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert hasattr(strategy, 'confidence_score')
    assert strategy.metadata.priority == 30  # Higher priority than rule-based


def test_ai_driven_has_providers():
    """Test that AI providers list is initialized"""
    from agents.strategies.ai_driven import AIDrivenStrategy

    strategy = AIDrivenStrategy()

    assert hasattr(strategy, 'ai_providers')
    assert isinstance(strategy.ai_providers, list)


def test_ai_driven_analyze_state():
    """Test state analysis with screenshot support"""
    from agents.strategies.ai_driven import AIDrivenStrategy

    strategy = AIDrivenStrategy()

    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email Password",
        "inputs": [{"type": "email"}],
        "buttons": ["Weiter"],
    }

    analyzed = strategy.analyze_state(browser_state)

    assert "url" in analyzed
    assert analyzed["url"] == "https://accounts.google.com"
    assert "screenshot_available" in analyzed


def test_ai_driven_can_handle_with_providers():
    """Test can_handle returns True when providers available"""
    from agents.strategies.ai_driven import AIDrivenStrategy

    strategy = AIDrivenStrategy()

    # If providers available, should handle any state
    if strategy.ai_providers:
        assert strategy.can_handle({"url": "https://example.com"}) == True
    else:
        # Without providers, can't handle
        assert strategy.can_handle({"url": "https://example.com"}) == False


def test_ai_driven_decide_action_no_providers():
    """Test decision when no AI providers available"""
    from agents.strategies.ai_driven import AIDrivenStrategy

    strategy = AIDrivenStrategy()

    # Force no providers for test
    original_providers = strategy.ai_providers
    strategy.ai_providers = []

    task = {"description": "Login", "goal": "perform_login"}
    state = {"url": "https://example.com", "text": "Test", "inputs_count": 0, "buttons_count": 0}
    action = strategy.decide_action(task, state, [])

    # Should return low-confidence wait action
    assert action["type"] == "wait"
    assert action["confidence"] <= 0.2

    # Restore
    strategy.ai_providers = original_providers


def test_ai_driven_execute_action():
    """Test executing basic actions"""
    from agents.strategies.ai_driven import AIDrivenStrategy
    from unittest.mock import Mock

    strategy = AIDrivenStrategy()

    # Test wait action
    action = {"action": "wait", "details": {"seconds": 1}}
    result = strategy.execute_action(action, Mock())
    assert result["success"] == True

    # Test done action
    action = {"action": "done", "details": {"message": "Finished"}}
    result = strategy.execute_action(action, Mock())
    assert result["success"] == True
    assert result.get("completed") == True


def test_ai_driven_confidence_score():
    """Test confidence score calculation"""
    from agents.strategies.ai_driven import AIDrivenStrategy

    strategy = AIDrivenStrategy()

    score = strategy.confidence_score

    assert 0.0 <= score <= 1.0
    # Without providers, should be low
    if not strategy.ai_providers:
        assert score <= 0.2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])