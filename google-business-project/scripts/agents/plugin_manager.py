#!/usr/bin/env python3
"""
Plugin Manager for Google Business Agent

Handles plugin discovery, registration, and lifecycle management.
"""

import importlib
import importlib.util
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginRegistry


class PluginManager:
    """
    Manages plugin discovery, loading, and lifecycle.

    The PluginManager:
    - Discovers plugins in configured directories
    - Registers plugins with the PluginRegistry
    - Provides access to plugins by type
    - Selects the best plugin for a given browser state
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """
        Initialize the plugin manager.

        Args:
            plugin_dirs: Optional list of directories to search for plugins.
                        Defaults to standard agent directories.
        """
        self.logger = logging.getLogger(__name__)
        self.registry = PluginRegistry()
        self.plugin_dirs = plugin_dirs or [
            "agents/strategies",
            "agents/analyzers",
            "agents/executors",
            "agents/handlers"
        ]
        self.logger.info(f"PluginManager initialized with directories: {self.plugin_dirs}")

    def register_plugin(self, plugin: BaseStrategyPlugin) -> None:
        """
        Register a single plugin.

        Args:
            plugin: Plugin instance to register
        """
        self.registry.register(plugin)
        self.logger.info(f"Registered plugin: {plugin.metadata.name} "
                        f"(type: {plugin.metadata.plugin_type.value}, "
                        f"priority: {plugin.metadata.priority})")

    def register_plugins(self, plugins: List[BaseStrategyPlugin]) -> None:
        """
        Register multiple plugins.

        Args:
            plugins: List of plugin instances to register
        """
        for plugin in plugins:
            self.register_plugin(plugin)

    def discover_plugins(self) -> List[BaseStrategyPlugin]:
        """
        Discover plugins in configured directories.

        Searches for Python files in plugin directories and loads
        classes that inherit from BaseStrategyPlugin.

        Returns:
            List of discovered plugin instances
        """
        discovered = []

        for plugin_dir in self.plugin_dirs:
            dir_path = Path(plugin_dir)
            if not dir_path.exists():
                self.logger.debug(f"Plugin directory not found: {plugin_dir}")
                continue

            # Look for Python files in directory
            for file_path in dir_path.glob("*.py"):
                if file_path.name.startswith("_") or file_path.name == "__init__.py":
                    continue

                module_name = file_path.stem
                try:
                    # Import module
                    spec = importlib.util.spec_from_file_location(
                        f"agents.{plugin_dir.replace('/', '.')}.{module_name}",
                        file_path
                    )
                    if spec is None or spec.loader is None:
                        self.logger.warning(f"Could not load spec for {file_path}")
                        continue

                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Find plugin classes (subclasses of BaseStrategyPlugin)
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (isinstance(attr, type) and
                            issubclass(attr, BaseStrategyPlugin) and
                            attr != BaseStrategyPlugin):
                            try:
                                plugin_instance = attr()
                                discovered.append(plugin_instance)
                                self.logger.info(f"Discovered plugin: {attr_name} from {file_path}")
                            except Exception as e:
                                self.logger.error(f"Failed to instantiate plugin {attr_name}: {e}")
                except Exception as e:
                    self.logger.error(f"Failed to load module {file_path}: {e}")

        return discovered

    def load_plugins(self) -> None:
        """
        Discover and register all plugins.

        This is the main entry point for loading plugins from directories.
        """
        plugins = self.discover_plugins()
        self.register_plugins(plugins)
        self.logger.info(f"Loaded {len(plugins)} plugins")

    def get_plugins(self, plugin_type: Optional[PluginType] = None) -> List[BaseStrategyPlugin]:
        """
        Get plugins from registry, optionally filtered by type.

        Args:
            plugin_type: Optional plugin type to filter by

        Returns:
            List of plugin instances
        """
        return self.registry.get_plugins(plugin_type)

    def get_best_plugin(self, browser_state: Dict[str, Any],
                        plugin_type: PluginType) -> Optional[BaseStrategyPlugin]:
        """
        Get the best plugin for the current browser state.

        Args:
            browser_state: Current browser state dictionary
            plugin_type: Type of plugin needed

        Returns:
            Best matching plugin or None if no suitable plugin found
        """
        return self.registry.get_best_plugin(browser_state, plugin_type)

    def reload_plugins(self) -> None:
        """
        Reload all plugins.

        Clears the registry and redisCOVERS plugins from directories.
        """
        self.registry.clear()
        self.load_plugins()
        self.logger.info("Plugins reloaded")

    def get_plugin_count(self) -> int:
        """Get the number of registered plugins."""
        return len(self.registry)

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """
        Get information about all registered plugins.

        Returns:
            List of plugin info dictionaries
        """
        plugins = self.get_plugins()
        return [
            {
                "name": p.metadata.name,
                "version": p.metadata.version,
                "type": p.metadata.plugin_type.value,
                "description": p.metadata.description,
                "priority": p.metadata.priority,
                "confidence": p.confidence_score
            }
            for p in plugins
        ]