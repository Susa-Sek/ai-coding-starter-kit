#!/usr/bin/env python3
"""
End-to-End smoke tests for the Google Business Agent.

These tests verify the complete workflow without actually running a browser.
They use mocks to simulate browser behavior.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_smoke_import_all_modules():
    """Smoke test: Verify all modules can be imported"""
    # Core modules
    from core.config import Config
    from core.logger import setup_logger
    from core.errors import GoogleBusinessAgentError
    from core.plugin_base import BaseStrategyPlugin, PluginRegistry, PluginType

    # Plugin system
    from agents.plugin_manager import PluginManager

    # Strategies
    from agents.strategies.rule_based import RuleBasedStrategy
    from agents.strategies.ai_driven import AIDrivenStrategy
    from agents.strategies.hybrid import HybridStrategy

    # Main agent
    from agents.new_ai_agent import NewAIAgent

    assert Config is not None
    assert BaseStrategyPlugin is not None
    assert PluginManager is not None
    assert RuleBasedStrategy is not None
    assert AIDrivenStrategy is not None
    assert HybridStrategy is not None
    assert NewAIAgent is not None


def test_smoke_strategy_plugin_loading():
    """Smoke test: Verify strategy plugins load correctly"""
    from agents.plugin_manager import PluginManager
    from core.plugin_base import PluginType

    manager = PluginManager()
    manager.load_plugins()

    strategies = manager.get_plugins(PluginType.STRATEGY)

    # Should have at least rule-based strategy
    assert len(strategies) >= 1, "At least one strategy should be loaded"


def test_smoke_agent_initialization():
    """Smoke test: Verify agent initializes correctly"""
    from agents.new_ai_agent import NewAIAgent

    agent = NewAIAgent("Test task description")

    assert agent.plugin_manager is not None
    assert agent.task is not None
    assert agent.logger is not None


def test_smoke_strategy_decision_flow():
    """Smoke test: Verify strategy can make decisions"""
    from agents.strategies.rule_based import RuleBasedStrategy

    strategy = RuleBasedStrategy()

    # Test state
    browser_state = {
        "url": "https://accounts.google.com/signin",
        "text": "Email",
        "inputs": [{"type": "email", "disabled": False, "value": ""}],
        "buttons": ["Weiter"],
        "has_email_field": True,
        "has_password_field": False
    }

    # Analyze state
    analyzed = strategy.analyze_state(browser_state)
    assert "url" in analyzed

    # Decide action
    task = {"description": "Login", "goal": "perform_login"}
    action = strategy.decide_action(task, analyzed, [])
    assert "type" in action
    assert "reasoning" in action


def test_smoke_strategy_execution():
    """Smoke test: Verify strategy can execute actions"""
    from agents.strategies.rule_based import RuleBasedStrategy
    from unittest.mock import Mock

    strategy = RuleBasedStrategy()

    # Mock browser page
    mock_page = Mock()
    mock_page.keyboard = Mock()
    mock_page.keyboard.press = Mock()

    # Test wait action
    action = {"type": "wait", "details": {"seconds": 1}}
    result = strategy.execute_action(action, mock_page)
    assert result["success"] == True

    # Test done action
    action = {"type": "done", "details": {"message": "Finished"}}
    result = strategy.execute_action(action, mock_page)
    assert result["success"] == True
    assert result.get("completed") == True


def test_smoke_hybrid_strategy():
    """Smoke test: Verify hybrid strategy combines sub-strategies"""
    from agents.strategies.hybrid import HybridStrategy

    strategy = HybridStrategy()

    # Should have sub-strategies
    assert len(strategy.strategies) >= 1

    # Should be able to analyze
    browser_state = {
        "url": "https://accounts.google.com",
        "text": "Email",
        "inputs": [],
        "buttons": []
    }

    analyzed = strategy.analyze_state(browser_state)
    assert "strategy_count" in analyzed


def test_smoke_complete_agent_flow():
    """Smoke test: Complete agent workflow without browser"""
    from agents.new_ai_agent import NewAIAgent
    from core.plugin_base import PluginType
    from unittest.mock import Mock

    # Create agent
    agent = NewAIAgent("Create Google Business Profile")

    # Verify initialization
    assert agent.plugin_manager is not None

    # Verify strategies loaded
    strategies = agent.plugin_manager.get_plugins(PluginType.STRATEGY)
    assert len(strategies) >= 1

    # Test strategy selection
    google_state = {
        "url": "https://accounts.google.com",
        "text": "Email Password",
        "inputs": [],
        "buttons": []
    }

    strategy = agent._select_strategy(google_state)
    # Strategy may or may not be found depending on can_handle
    if strategy:
        assert hasattr(strategy, 'metadata')
        assert hasattr(strategy, 'confidence_score')


def test_smoke_task_parsing():
    """Smoke test: Verify task descriptions are parsed"""
    from agents.new_ai_agent import NewAIAgent

    # Different task types
    tasks = [
        "Create a Google Business Profile",
        "Login to Google account",
        "Update business information"
    ]

    for task_desc in tasks:
        agent = NewAIAgent(task_desc)
        assert agent.task is not None
        assert agent.task.description == task_desc


def test_smoke_browser_state_structure():
    """Smoke test: Verify browser state structure"""
    from agents.new_ai_agent import NewAIAgent
    from unittest.mock import Mock

    agent = NewAIAgent("Test")

    # Mock browser with complete state
    mock_page = Mock()
    mock_page.url = "https://business.google.com/dashboard"
    mock_page.title.return_value = "Dashboard"

    # Mock locator for body
    body_locator = Mock()
    body_locator.count.return_value = 1
    body_locator.inner_text.return_value = "Dashboard content"
    body_locator.all.return_value = []

    # Mock locator for inputs
    input_locator = Mock()
    input_locator.all.return_value = []

    # Mock locator for buttons
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

    # Verify state structure
    assert "url" in state
    assert "title" in state
    assert "text" in state
    assert "inputs" in state
    assert "buttons" in state


def test_smoke_plugin_registry():
    """Smoke test: Verify plugin registry works correctly"""
    from core.plugin_base import BaseStrategyPlugin, PluginRegistry, PluginType

    registry = PluginRegistry()

    # Create mock plugins
    class MockStrategy(BaseStrategyPlugin):
        def __init__(self):
            super().__init__()
            self.metadata.name = "MockStrategy"
            self.metadata.plugin_type = PluginType.STRATEGY
            self.metadata.priority = 50

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"type": "wait"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.8

        def can_handle(self, browser_state):
            return True

    # Register plugin
    plugin = MockStrategy()
    registry.register(plugin)

    # Verify registration
    assert len(registry.get_plugins()) == 1
    assert registry.get_plugins(PluginType.STRATEGY)[0] == plugin

    # Verify best plugin selection
    best = registry.get_best_plugin({"url": "https://example.com"}, PluginType.STRATEGY)
    assert best == plugin


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])