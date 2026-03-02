#!/usr/bin/env python3
"""
Tests for plugin manager.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_plugin_manager_registration():
    """Test plugin registration and retrieval"""
    from agents.plugin_manager import PluginManager
    from core.plugin_base import BaseStrategyPlugin, PluginType

    # Create a mock plugin class
    class MockPlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'MockPlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Mock plugin for testing',
                'author': 'Test',
                'priority': 50
            })()

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"action": "wait"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.8

        def can_handle(self, browser_state):
            return True

    manager = PluginManager()
    plugin = MockPlugin()

    manager.register_plugin(plugin)

    # Get all plugins
    plugins = manager.get_plugins(PluginType.STRATEGY)
    assert len(plugins) == 1
    assert plugins[0] == plugin

    # Get best plugin
    browser_state = {"url": "https://example.com"}
    best = manager.get_best_plugin(browser_state, PluginType.STRATEGY)
    assert best == plugin


def test_plugin_manager_discovery():
    """Test plugin discovery from directories"""
    from agents.plugin_manager import PluginManager
    from core.plugin_base import PluginType

    manager = PluginManager(plugin_dirs=[])  # Empty dirs to avoid actual discovery

    # Should not crash with empty dirs
    plugins = manager.get_plugins()
    assert isinstance(plugins, list)


def test_plugin_manager_best_selection():
    """Test that best plugin is selected based on priority and confidence"""
    from agents.plugin_manager import PluginManager
    from core.plugin_base import BaseStrategyPlugin, PluginType

    class HighPriorityPlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'HighPriorityPlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'High priority plugin',
                'author': 'Test',
                'priority': 10  # Higher priority (lower number)
            })()

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"action": "high_priority"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.9

        def can_handle(self, browser_state):
            return True

    class LowPriorityPlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'LowPriorityPlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Low priority plugin',
                'author': 'Test',
                'priority': 100  # Lower priority (higher number)
            })()

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"action": "low_priority"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.5

        def can_handle(self, browser_state):
            return True

    manager = PluginManager()
    manager.register_plugin(LowPriorityPlugin())
    manager.register_plugin(HighPriorityPlugin())

    browser_state = {"url": "https://example.com"}
    best = manager.get_best_plugin(browser_state, PluginType.STRATEGY)

    # Should select high priority plugin
    assert best.metadata.name == "HighPriorityPlugin"


def test_plugin_manager_can_handle_filtering():
    """Test that plugins are filtered by can_handle"""
    from agents.plugin_manager import PluginManager
    from core.plugin_base import BaseStrategyPlugin, PluginType

    class GooglePlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'GooglePlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Google-specific plugin',
                'author': 'Test',
                'priority': 50
            })()

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"action": "google"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.9

        def can_handle(self, browser_state):
            return "google.com" in browser_state.get("url", "")

    class UniversalPlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'UniversalPlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Universal plugin',
                'author': 'Test',
                'priority': 100
            })()

        def analyze_state(self, browser_state):
            return {"analyzed": True}

        def decide_action(self, task, state, history):
            return {"action": "universal"}

        def execute_action(self, action, browser_page):
            return {"success": True}

        @property
        def confidence_score(self):
            return 0.5

        def can_handle(self, browser_state):
            return True

    manager = PluginManager()
    manager.register_plugin(UniversalPlugin())
    manager.register_plugin(GooglePlugin())

    # On Google URL, should select GooglePlugin (higher priority + can_handle)
    google_state = {"url": "https://accounts.google.com"}
    best = manager.get_best_plugin(google_state, PluginType.STRATEGY)
    assert best.metadata.name == "GooglePlugin"

    # On non-Google URL, should select UniversalPlugin (only one that can_handle)
    other_state = {"url": "https://example.com"}
    best = manager.get_best_plugin(other_state, PluginType.STRATEGY)
    assert best.metadata.name == "UniversalPlugin"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])