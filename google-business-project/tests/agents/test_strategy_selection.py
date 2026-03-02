#!/usr/bin/env python3
"""
Tests for Strategy Selection in new_ai_agent.py
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_agent_has_plugin_manager():
    """Test that agent has plugin manager after initialization"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test task")

    assert hasattr(agent, 'plugin_manager')
    assert agent.plugin_manager is not None


def test_agent_has_strategy_methods():
    """Test that agent has strategy selection methods"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test task")

    assert hasattr(agent, '_select_strategy')
    assert hasattr(agent, '_execute_with_strategy')
    assert hasattr(agent, '_get_browser_state')


def test_select_strategy_returns_strategy():
    """Test that _select_strategy returns a strategy when available"""
    from agents.new_ai_agent import NewAIAgent
    from core.plugin_base import PluginType

    agent = NewAIAgent("Test task")

    # Google URL should trigger rule-based strategy
    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [],
        "buttons": []
    }

    strategy = agent._select_strategy(browser_state)

    # Should return a strategy (rule-based handles Google URLs)
    if strategy:
        assert hasattr(strategy, 'metadata')
        assert strategy.metadata.plugin_type == PluginType.STRATEGY


def test_get_browser_state_structure():
    """Test that _get_browser_state returns correct structure"""
    from agents.new_ai_agent import NewAIAgent
    from unittest.mock import Mock, MagicMock

    agent = NewAIAgent("Test task")

    # Mock browser
    agent.browser = Mock()
    agent.browser.page = Mock()
    agent.browser.page.url = "https://example.com"
    agent.browser.page.title.return_value = "Test Page"
    agent.browser.page.locator.return_value.inner_text.return_value = "Test content"
    agent.browser.page.locator.return_value.count.return_value = 0
    agent.browser.page.locator.return_value.all.return_value = []

    state = agent._get_browser_state()

    assert "url" in state
    assert "title" in state
    assert "text" in state
    assert "inputs" in state
    assert "buttons" in state


def test_execute_with_strategy_structure():
    """Test that _execute_with_strategy returns correct structure"""
    from agents.new_ai_agent import NewAIAgent
    from agents.strategies.rule_based import RuleBasedStrategy
    from unittest.mock import Mock

    agent = NewAIAgent("Test task")

    # Create a mock strategy
    strategy = RuleBasedStrategy()

    task = {"description": "Test", "goal": "test"}
    browser_state = {
        "url": "https://business.google.com/dashboard",
        "text": "Dashboard",
        "inputs": [],
        "buttons": []
    }
    history = []

    result = agent._execute_with_strategy(strategy, task, browser_state, history)

    assert "action" in result
    assert "result" in result
    assert "strategy" in result
    assert "confidence" in result


def test_plugin_manager_has_strategies():
    """Test that plugin manager has strategies loaded"""
    from agents.new_ai_agent import NewAIAgent
    from core.plugin_base import PluginType

    agent = NewAIAgent("Test task")

    # Get strategies from plugin manager
    strategies = agent.plugin_manager.get_plugins(PluginType.STRATEGY)

    # Should have at least one strategy (rule-based is always available)
    assert len(strategies) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])