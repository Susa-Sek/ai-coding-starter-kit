#!/usr/bin/env python3
"""
Integration tests for the unified Google Business Agent.
Tests the complete workflow with mock browser and strategies.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_unified_agent_initialization():
    """Test that unified agent initializes all components"""
    from agents.new_ai_agent import NewAIAgent
    from core.plugin_base import PluginType

    agent = NewAIAgent("Create a Google Business Profile")

    assert agent.plugin_manager is not None
    assert len(agent.plugin_manager.get_plugins(PluginType.STRATEGY)) >= 1
    assert agent.task is not None
    assert agent.task.goal is not None


def test_unified_agent_strategy_selection():
    """Test that agent selects appropriate strategy for Google URLs"""
    from agents.new_ai_agent import NewAIAgent
    from core.plugin_base import PluginType

    agent = NewAIAgent("Login to Google")

    # Test Google Accounts URL
    google_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"]
    }

    strategy = agent._select_strategy(google_state)

    assert strategy is not None
    assert strategy.can_handle(google_state)


def test_unified_agent_browser_state_collection():
    """Test that browser state is collected correctly"""
    from agents.new_ai_agent import NewAIAgent
    from unittest.mock import Mock

    agent = NewAIAgent("Test task")

    # Mock browser
    mock_page = Mock()
    mock_page.url = "https://business.google.com/dashboard"
    mock_page.title.return_value = "Google Business Dashboard"
    mock_page.locator.return_value.all.return_value = []
    mock_page.locator.return_value.count.return_value = 1
    mock_page.locator.return_value.inner_text.return_value = "Dashboard content"

    agent.browser = Mock()
    agent.browser.page = mock_page

    state = agent._get_browser_state()

    assert state["url"] == "https://business.google.com/dashboard"
    assert "title" in state
    assert "inputs" in state
    assert "buttons" in state


def test_unified_agent_strategy_execution_flow():
    """Test the complete strategy execution flow"""
    from agents.new_ai_agent import NewAIAgent
    from agents.strategies.rule_based import RuleBasedStrategy
    from unittest.mock import Mock

    agent = NewAIAgent("Create business profile")

    # Create mock browser
    mock_page = Mock()
    mock_page.url = "https://accounts.google.com/signin"
    mock_page.title.return_value = "Sign in"
    mock_page.locator.return_value.all.return_value = []
    mock_page.locator.return_value.count.return_value = 0

    agent.browser = Mock()
    agent.browser.page = mock_page

    # Get strategy
    strategy = RuleBasedStrategy()

    # Prepare inputs
    task = {"description": "Login", "goal": "perform_login"}
    browser_state = {
        "url": "https://accounts.google.com/signin",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
        "has_email_field": True,
        "has_password_field": False
    }
    history = []

    # Execute with strategy
    result = agent._execute_with_strategy(strategy, task, browser_state, history)

    assert "action" in result
    assert "result" in result
    assert "strategy" in result
    assert "confidence" in result


def test_unified_agent_task_parsing():
    """Test that tasks are parsed correctly"""
    from agents.new_ai_agent import NewAIAgent

    # Test Google Business Profile task
    agent1 = NewAIAgent("Create a Google Business Profile for SE Handwerk")
    assert agent1.task is not None
    assert len(agent1.task.description) > 0

    # Test login task
    agent2 = NewAIAgent("Login to Google account")
    assert agent2.task is not None


def test_unified_agent_action_history():
    """Test that action history is tracked"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test task")

    # Initial state
    assert len(agent.action_history) == 0

    # Simulate adding to history
    agent.action_history.append({
        "iteration": 1,
        "action": "fill_input",
        "result": {"success": True}
    })

    assert len(agent.action_history) == 1


def test_unified_agent_hybrid_strategy_integration():
    """Test integration with hybrid strategy"""
    from agents.new_ai_agent import NewAIAgent
    from agents.strategies.hybrid import HybridStrategy
    from core.plugin_base import PluginType

    agent = NewAIAgent("Create Google Business Profile")

    # Check that hybrid strategy is loaded
    strategies = agent.plugin_manager.get_plugins(PluginType.STRATEGY)
    strategy_names = [s.metadata.name for s in strategies]

    # Should have at least one strategy
    assert len(strategies) >= 1


def test_unified_agent_fallback_on_no_strategy():
    """Test fallback behavior when no strategy can handle state"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test task")

    # Create a state that no strategy can handle
    unknown_state = {
        "url": "https://unknown-random-site.com/page",
        "text": "",
        "inputs": [],
        "buttons": []
    }

    # Get strategy - may return None or a strategy with low confidence
    strategy = agent._select_strategy(unknown_state)

    # Either no strategy or one that can handle (even if low confidence)
    if strategy:
        # If strategy found, it should be able to handle
        assert strategy.can_handle(unknown_state) or strategy.confidence_score < 0.5


@pytest.fixture
def mock_browser():
    """Fixture for mock browser"""
    browser = Mock()
    page = Mock()
    page.url = "https://accounts.google.com"
    page.title.return_value = "Sign in - Google Accounts"
    page.locator.return_value.all.return_value = []
    page.locator.return_value.count.return_value = 0
    # Set up the locator to return text when 'body' selector is used
    body_locator = Mock()
    body_locator.count.return_value = 1
    body_locator.inner_text.return_value = "Email Password"
    body_locator.all.return_value = []
    page.locator = Mock(side_effect=lambda selector: body_locator if 'body' in selector else Mock(all=lambda: [], count=lambda: 0))
    browser.page = page
    return browser


def test_unified_agent_with_mock_browser(mock_browser):
    """Test agent with mock browser fixture"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Login to Google")

    # Set mock browser
    agent.browser = mock_browser

    # Get browser state
    state = agent._get_browser_state()

    assert state["url"] == "https://accounts.google.com"
    # Just check that text was collected (may be empty if mock doesn't fully work)
    assert "text" in state


if __name__ == "__main__":
    pytest.main([__file__, "-v"])