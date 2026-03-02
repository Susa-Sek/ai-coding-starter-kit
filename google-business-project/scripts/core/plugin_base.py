#!/usr/bin/env python3
"""
Plugin Base Module for Google Business Agent

Provides base classes and registry for the plugin architecture.
Strategy plugins implement decision-making logic for browser automation.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PluginType(Enum):
    """Types of plugins supported by the system."""
    STRATEGY = "strategy"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    HANDLER = "handler"


@dataclass
class PluginMetadata:
    """Metadata for a plugin."""
    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    priority: int = 100  # Lower = higher priority


class BaseStrategyPlugin(ABC):
    """
    Base class for all strategy plugins.

    Strategy plugins implement the decision-making logic for browser automation.
    They analyze the current browser state, decide on the next action, and execute it.

    The plugin system allows different strategies to be swapped dynamically:
    - Rule-based strategies use pattern matching and heuristics
    - AI-driven strategies use vision models for decision making
    - Hybrid strategies combine multiple approaches
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the strategy plugin.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.metadata = PluginMetadata(
            name=self.__class__.__name__,
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Base strategy plugin",
            author="System",
            priority=100
        )

    @abstractmethod
    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the current browser state and return structured analysis.

        Args:
            browser_state: Dictionary containing:
                - url: Current page URL
                - title: Page title
                - text: Page text content
                - inputs: List of visible input elements
                - buttons: List of visible buttons
                - screenshot_b64: Optional base64-encoded screenshot

        Returns:
            Dictionary with analyzed state information
        """
        pass

    @abstractmethod
    def decide_action(self,
                     task: Dict[str, Any],
                     current_state: Dict[str, Any],
                     history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Decide the next action based on task, current state, and history.

        Args:
            task: Task description and parameters
                - description: Human-readable task description
                - goal: Structured goal
                - parameters: Task-specific parameters
            current_state: Analyzed browser state from analyze_state()
            history: List of previous actions and results

        Returns:
            Dictionary with action:
                - type: Action type (fill, click, wait, etc.)
                - details: Action-specific parameters
                - reasoning: Human-readable explanation
                - confidence: Confidence score (0.0-1.0)
        """
        pass

    @abstractmethod
    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """
        Execute an action on the browser page.

        Args:
            action: Action dictionary from decide_action()
            browser_page: Playwright/Camoufox page object

        Returns:
            Dictionary with result:
                - success: True if action succeeded
                - message: Human-readable result message
                - error: Error message if failed
                - requires_user: True if user interaction needed
                - completed: True if task is complete
        """
        pass

    @property
    @abstractmethod
    def confidence_score(self) -> float:
        """
        Get the confidence score for this plugin (0.0-1.0).

        Higher scores indicate more confidence in the plugin's decisions.
        Used by the registry to select the best plugin for a given state.

        Returns:
            Confidence score between 0.0 and 1.0
        """
        pass

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """
        Check if this plugin can handle the current browser state.

        Override this method to implement state-specific capability checks.
        For example, a Google-specific plugin might only handle google.com URLs.

        Args:
            browser_state: Current browser state dictionary

        Returns:
            True if this plugin can handle the state
        """
        return True


class PluginRegistry:
    """
    Registry for managing plugins.

    The registry handles:
    - Plugin registration and discovery
    - Plugin lookup by type
    - Best plugin selection based on confidence and capability
    """

    def __init__(self):
        """Initialize the plugin registry."""
        self._plugins: Dict[str, BaseStrategyPlugin] = {}
        self._plugin_types: Dict[PluginType, List[str]] = {pt: [] for pt in PluginType}

    def register(self, plugin: BaseStrategyPlugin) -> None:
        """
        Register a plugin with the registry.

        Args:
            plugin: Plugin instance to register
        """
        plugin_id = f"{plugin.metadata.plugin_type.value}:{plugin.metadata.name}"
        self._plugins[plugin_id] = plugin

        # Add to type index
        self._plugin_types[plugin.metadata.plugin_type].append(plugin_id)

    def unregister(self, plugin_id: str) -> bool:
        """
        Unregister a plugin by ID.

        Args:
            plugin_id: Plugin ID to unregister

        Returns:
            True if plugin was found and removed
        """
        if plugin_id in self._plugins:
            plugin = self._plugins[plugin_id]
            del self._plugins[plugin_id]
            self._plugin_types[plugin.metadata.plugin_type].remove(plugin_id)
            return True
        return False

    def get_plugins(self, plugin_type: Optional[PluginType] = None) -> List[BaseStrategyPlugin]:
        """
        Get plugins, optionally filtered by type.

        Args:
            plugin_type: Optional plugin type to filter by

        Returns:
            List of plugin instances
        """
        if plugin_type:
            plugin_ids = self._plugin_types.get(plugin_type, [])
            return [self._plugins[pid] for pid in plugin_ids if pid in self._plugins]
        return list(self._plugins.values())

    def get_plugin(self, plugin_id: str) -> Optional[BaseStrategyPlugin]:
        """
        Get a specific plugin by ID.

        Args:
            plugin_id: Plugin ID

        Returns:
            Plugin instance or None if not found
        """
        return self._plugins.get(plugin_id)

    def get_best_plugin(self, browser_state: Dict[str, Any],
                        plugin_type: PluginType) -> Optional[BaseStrategyPlugin]:
        """
        Get the best plugin for the current browser state.

        Selection criteria:
        1. Plugin must be able to handle the state (can_handle returns True)
        2. Sort by priority (lower = higher priority)
        3. Sort by confidence score (higher = better)

        Args:
            browser_state: Current browser state dictionary
            plugin_type: Type of plugin needed

        Returns:
            Best matching plugin or None if no suitable plugin found
        """
        candidates = self.get_plugins(plugin_type)

        # Filter to plugins that can handle this state
        suitable = [p for p in candidates if p.can_handle(browser_state)]

        if not suitable:
            return None

        # Sort by priority (ascending) and confidence (descending)
        suitable.sort(key=lambda p: (p.metadata.priority, -p.confidence_score))

        return suitable[0]

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._plugin_types = {pt: [] for pt in PluginType}

    def __len__(self) -> int:
        """Get the number of registered plugins."""
        return len(self._plugins)

    def __contains__(self, plugin_id: str) -> bool:
        """Check if a plugin is registered."""
        return plugin_id in self._plugins