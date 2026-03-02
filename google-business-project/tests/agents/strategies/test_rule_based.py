#!/usr/bin/env python3
"""
Tests for Rule-Based Strategy Plugin.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'scripts'))


def test_rule_based_strategy_creation():
    """Test rule-based strategy plugin creation"""
    from agents.strategies.rule_based import RuleBasedStrategy
    from core.plugin_base import PluginType

    strategy = RuleBasedStrategy()

    assert strategy.metadata.name == "RuleBasedStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert strategy.confidence_score >= 0.0
    assert strategy.confidence_score <= 1.0
    assert strategy.metadata.priority == 50  # Medium priority


def test_rule_based_can_handle():
    """Test can_handle method for different URLs"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Should handle Google login pages
    google_state = {"url": "https://accounts.google.com", "text": "Email"}
    assert strategy.can_handle(google_state) == True

    # Should handle Google Business pages
    business_state = {"url": "https://business.google.com", "text": "Create Profile"}
    assert strategy.can_handle(business_state) == True

    # Should handle German text patterns
    german_state = {"url": "https://example.com", "text": "Weiter Email Passwort"}
    assert strategy.can_handle(german_state) == True


def test_rule_based_analyze_state():
    """Test state analysis"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email Password",
        "inputs": [
            {"type": "email", "placeholder": "Email", "disabled": False}
        ],
        "buttons": ["Weiter", "Hilfe"]
    }

    analyzed = strategy.analyze_state(browser_state)

    assert "url" in analyzed
    assert analyzed["url"] == "https://accounts.google.com"
    assert "has_password_field" in analyzed
    assert "has_email_field" in analyzed


def test_rule_based_decide_action_google_login():
    """Test decision making for Google login flow"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Email page
    email_state = {
        "url": "https://accounts.google.com/signin",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
        "has_email_field": True,
        "has_password_field": False
    }

    task = {"description": "Login to Google", "goal": "perform_login"}
    action = strategy.decide_action(task, email_state, [])

    assert action["type"] == "fill_input"
    assert "value" in action["details"]


def test_rule_based_decide_action_2fa():
    """Test decision making for 2FA challenge"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # 2FA challenge page
    challenge_state = {
        "url": "https://accounts.google.com/challenge",
        "text": "Bestätigen Sie auf Ihrem Pixel: 42",
        "inputs": [],
        "buttons": [],
        "has_email_field": False,
        "has_password_field": False
    }

    task = {"description": "Login to Google", "goal": "perform_login"}
    action = strategy.decide_action(task, challenge_state, [])

    assert action["type"] == "wait_for_user"
    assert "42" in action["details"]["message"] or action["details"].get("number") == "42"


def test_rule_based_decide_action_dashboard():
    """Test completion detection on dashboard"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Dashboard page
    dashboard_state = {
        "url": "https://business.google.com/dashboard",
        "text": "Your locations",
        "inputs": [],
        "buttons": [],
        "has_email_field": False,
        "has_password_field": False
    }

    task = {"description": "Create business profile", "goal": "create_profile"}
    action = strategy.decide_action(task, dashboard_state, [])

    assert action["type"] == "done"


def test_rule_based_execute_action_fill():
    """Test executing fill input action"""
    from agents.strategies.rule_based import RuleBasedStrategy
    from unittest.mock import Mock

    strategy = RuleBasedStrategy()

    action = {
        "type": "fill_input",
        "details": {"index": 0, "value": "test@example.com"}
    }

    # Mock page
    mock_page = Mock()
    mock_input = Mock()
    mock_input.is_disabled.return_value = False
    mock_page.locator.return_value.all.return_value = [mock_input]

    result = strategy.execute_action(action, mock_page)

    assert result["success"] == True


def test_rule_based_execute_action_click():
    """Test executing click button action"""
    from agents.strategies.rule_based import RuleBasedStrategy
    from unittest.mock import Mock

    strategy = RuleBasedStrategy()

    action = {
        "type": "click_button",
        "details": {"text": "Weiter"}
    }

    # Mock page
    mock_page = Mock()

    result = strategy.execute_action(action, mock_page)

    assert result["success"] == True


def test_rule_based_stuck_detection():
    """Test that stuck detection works through analyze_state"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Same URL repeated - need to call analyze_state to track consecutive URLs
    raw_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
    }

    # Simulate being stuck by calling analyze_state multiple times
    # which increments consecutive_same_url counter
    strategy.analyze_state(raw_state)  # 1st time
    strategy.analyze_state(raw_state)  # 2nd time
    strategy.analyze_state(raw_state)  # 3rd time
    strategy.analyze_state(raw_state)  # 4th time - should now be > 3

    # Now analyze and decide
    analyzed = strategy.analyze_state(raw_state)  # 5th time, consecutive_same_url > 3
    action = strategy.decide_action({"goal": "login"}, analyzed, [])

    # After 3+ same URLs, should try pressing enter
    assert action["type"] == "press_enter"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])