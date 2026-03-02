#!/usr/bin/env python3
"""
Tests for base plugin interface.
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))


def test_base_plugin_interface():
    """Test that BaseStrategyPlugin is abstract and requires implementation"""
    from core.plugin_base import BaseStrategyPlugin, PluginRegistry
    import inspect

    # Verify BaseStrategyPlugin is abstract
    assert inspect.isabstract(BaseStrategyPlugin), "BaseStrategyPlugin should be abstract"

    # Verify required abstract methods exist
    abstract_methods = BaseStrategyPlugin.__abstractmethods__
    assert 'analyze_state' in abstract_methods
    assert 'decide_action' in abstract_methods
    assert 'execute_action' in abstract_methods
    assert 'confidence_score' in abstract_methods

    # Verify we can't instantiate directly
    with pytest.raises(TypeError):
        BaseStrategyPlugin()


def test_plugin_metadata():
    """Test that plugin metadata is properly structured"""
    from core.plugin_base import PluginMetadata, PluginType

    metadata = PluginMetadata(
        name="TestPlugin",
        version="1.0.0",
        plugin_type=PluginType.STRATEGY,
        description="Test plugin",
        author="Test",
        priority=50
    )

    assert metadata.name == "TestPlugin"
    assert metadata.version == "1.0.0"
    assert metadata.plugin_type == PluginType.STRATEGY
    assert metadata.priority == 50


def test_plugin_registry():
    """Test plugin registration and retrieval"""
    from core.plugin_base import PluginRegistry, PluginType, BaseStrategyPlugin

    # Create a mock plugin class
    class MockPlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'MockPlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Mock',
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

    registry = PluginRegistry()
    plugin = MockPlugin()
    registry.register(plugin)

    # Get all plugins
    plugins = registry.get_plugins()
    assert len(plugins) == 1
    assert plugins[0] == plugin

    # Get by type
    strategy_plugins = registry.get_plugins(PluginType.STRATEGY)
    assert len(strategy_plugins) == 1

    # Get best plugin
    browser_state = {"url": "https://example.com"}
    best = registry.get_best_plugin(browser_state, PluginType.STRATEGY)
    assert best == plugin


def test_plugin_can_handle():
    """Test that plugins can indicate capability"""
    from core.plugin_base import BaseStrategyPlugin, PluginType

    class SelectivePlugin(BaseStrategyPlugin):
        def __init__(self):
            self.config = {}
            self.metadata = type('Metadata', (), {
                'name': 'SelectivePlugin',
                'version': '1.0.0',
                'plugin_type': PluginType.STRATEGY,
                'description': 'Selective',
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
            url = browser_state.get("url", "")
            return "google.com" in url

    plugin = SelectivePlugin()

    # Should handle Google URLs
    assert plugin.can_handle({"url": "https://accounts.google.com"}) == True

    # Should not handle other URLs
    assert plugin.can_handle({"url": "https://example.com"}) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])