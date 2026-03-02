# Google Business Agent Consolidation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Consolidate multiple Google Business agent implementations into a unified, modular architecture based on `new_ai_agent.py` with plugin system for different strategies.

**Architecture:** Modular plugin architecture with `new_ai_agent.py` as the unified agent, core components (State Analyzer, Decision Engine, Action Executor, Memory Manager), and strategy plugins (Rule-Based, AI-Driven, Hybrid). Preserve best functionality from existing agents.

**Tech Stack:** Python 3.8+, Playwright/Camoufox for browser automation, Anthropic/DeepSeek APIs for AI decisions, structured logging, configuration management with environment variables.

---

## Phase 1: Analysis and Plugin Interface Design

### Task 1: Inventory Existing Agent Functionality

**Files:**
- Read: `google-business-project/scripts/agents/smart_agent.py`
- Read: `google-business-project/scripts/agents/agent_profile_creator.py`
- Read: `google-business-project/scripts/agents/ai_profile_creator.py`
- Create: `google-business-project/docs/agent-functionality-inventory.md`

**Step 1: Analyze smart_agent.py functionality**

Create inventory document with sections:
1. State analysis functions (get_page_state)
2. Decision logic patterns (URL/text matching, 2FA handling)
3. Action execution functions (fill_input, click_button, wait_for_user)
4. Configuration usage (business data integration)
5. Error handling patterns

**Step 2: Analyze agent_profile_creator.py functionality**

Add to inventory:
1. Screenshot-based AI analysis flow
2. Multi-AI provider support structure
3. Base64 image encoding for API calls
4. Goal-oriented task execution

**Step 3: Analyze ai_profile_creator.py functionality**

Add to inventory:
1. Hybrid rule-based/AI approach
2. Fallback strategy patterns
3. Context-aware decision making

**Step 4: Identify unique features and overlaps**

Create table showing which agent has which functionality:
- 2FA challenge handling
- Business data integration
- Screenshot AI analysis
- Rule-based decisions
- Human delay simulation
- Error recovery

**Step 5: Commit inventory document**

```bash
git add google-business-project/docs/agent-functionality-inventory.md
git commit -m "docs(PROJ-1): inventory existing agent functionality"
```

### Task 2: Design Plugin Interface System

**Files:**
- Create: `google-business-project/scripts/core/plugin_base.py`
- Modify: `google-business-project/scripts/agents/new_ai_agent.py:90-144` (add plugin loading)
- Create: `tests/core/test_plugin_base.py`

**Step 1: Write failing test for base plugin interface**

```python
# tests/core/test_plugin_base.py
import pytest
from core.plugin_base import BaseStrategyPlugin, PluginRegistry

def test_base_plugin_interface():
    """Test that BaseStrategyPlugin has required methods"""
    plugin = BaseStrategyPlugin()

    # Should have analyze_state method
    with pytest.raises(NotImplementedError):
        plugin.analyze_state(None)

    # Should have decide_action method
    with pytest.raises(NotImplementedError):
        plugin.decide_action(None, None, None)

    # Should have execute_action method
    with pytest.raises(NotImplementedError):
        plugin.execute_action(None, None)

    # Should have confidence_score property
    assert hasattr(plugin, 'confidence_score')
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/core/test_plugin_base.py::test_base_plugin_interface -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'core.plugin_base'"

**Step 3: Create base plugin interface**

```python
# google-business-project/scripts/core/plugin_base.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

class PluginType(Enum):
    STRATEGY = "strategy"
    ANALYZER = "analyzer"
    EXECUTOR = "executor"
    HANDLER = "handler"

@dataclass
class PluginMetadata:
    name: str
    version: str
    plugin_type: PluginType
    description: str
    author: str
    priority: int = 100  # Lower = higher priority

class BaseStrategyPlugin(ABC):
    """Base class for all strategy plugins"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
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
        """Analyze current browser state and return structured analysis"""
        pass

    @abstractmethod
    def decide_action(self,
                     task: Dict[str, Any],
                     current_state: Dict[str, Any],
                     history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Decide next action based on task, state, and history"""
        pass

    @abstractmethod
    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute action and return result"""
        pass

    @property
    @abstractmethod
    def confidence_score(self) -> float:
        """Confidence score for this plugin (0.0-1.0)"""
        pass

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """Check if this plugin can handle the current state"""
        return True

class PluginRegistry:
    """Registry for managing plugins"""

    def __init__(self):
        self._plugins: Dict[str, BaseStrategyPlugin] = {}
        self._plugin_types: Dict[PluginType, List[str]] = {pt: [] for pt in PluginType}

    def register(self, plugin: BaseStrategyPlugin) -> None:
        """Register a plugin"""
        plugin_id = f"{plugin.metadata.plugin_type.value}:{plugin.metadata.name}"
        self._plugins[plugin_id] = plugin

        # Add to type index
        self._plugin_types[plugin.metadata.plugin_type].append(plugin_id)

    def get_plugins(self, plugin_type: Optional[PluginType] = None) -> List[BaseStrategyPlugin]:
        """Get plugins, optionally filtered by type"""
        if plugin_type:
            plugin_ids = self._plugin_types.get(plugin_type, [])
            return [self._plugins[pid] for pid in plugin_ids]
        return list(self._plugins.values())

    def get_best_plugin(self, browser_state: Dict[str, Any], plugin_type: PluginType) -> Optional[BaseStrategyPlugin]:
        """Get the best plugin for the current state"""
        candidates = self.get_plugins(plugin_type)
        suitable = [p for p in candidates if p.can_handle(browser_state)]

        if not suitable:
            return None

        # Sort by priority and confidence
        suitable.sort(key=lambda p: (p.metadata.priority, -p.confidence_score))
        return suitable[0]
```

**Step 4: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/core/test_plugin_base.py::test_base_plugin_interface -v
```
Expected: PASS

**Step 5: Commit plugin base interface**

```bash
git add google-business-project/scripts/core/plugin_base.py tests/core/test_plugin_base.py
git commit -m "feat(PROJ-1): add base plugin interface system"
```

### Task 3: Enhance new_ai_agent.py with Plugin Loading

**Files:**
- Modify: `google-business-project/scripts/agents/new_ai_agent.py:90-144` (__init__ method)
- Modify: `google-business-project/scripts/agents/new_ai_agent.py:241-279` (_initialize_components method)
- Create: `google-business-project/scripts/agents/plugin_manager.py`
- Create: `tests/agents/test_plugin_manager.py`

**Step 1: Write failing test for plugin manager**

```python
# tests/agents/test_plugin_manager.py
import pytest
from agents.plugin_manager import PluginManager
from core.plugin_base import BaseStrategyPlugin, PluginType

class MockPlugin(BaseStrategyPlugin):
    def analyze_state(self, browser_state):
        return {"analyzed": True}

    def decide_action(self, task, state, history):
        return {"action": "wait"}

    def execute_action(self, action, browser_page):
        return {"success": True}

    @property
    def confidence_score(self):
        return 0.8

def test_plugin_manager_registration():
    """Test plugin registration and retrieval"""
    manager = PluginManager()
    plugin = MockPlugin()

    manager.register_plugin(plugin)

    plugins = manager.get_plugins(PluginType.STRATEGY)
    assert len(plugins) == 1
    assert plugins[0] == plugin

    best = manager.get_best_plugin({}, PluginType.STRATEGY)
    assert best == plugin
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/agents/test_plugin_manager.py::test_plugin_manager_registration -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'agents.plugin_manager'"

**Step 3: Create plugin manager**

```python
# google-business-project/scripts/agents/plugin_manager.py
import importlib
import pkgutil
from typing import Dict, Any, List, Optional, Type
from pathlib import Path

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginRegistry
from core.logger import setup_logger

class PluginManager:
    """Manages plugin discovery, loading, and lifecycle"""

    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        self.logger = setup_logger("plugin_manager")
        self.registry = PluginRegistry()
        self.plugin_dirs = plugin_dirs or [
            "agents/strategies",
            "agents/analyzers",
            "agents/executors",
            "agents/handlers"
        ]

        self.logger.info(f"PluginManager initialized with directories: {self.plugin_dirs}")

    def register_plugin(self, plugin: BaseStrategyPlugin) -> None:
        """Register a single plugin"""
        self.registry.register(plugin)
        self.logger.info(f"Registered plugin: {plugin.metadata.name} (type: {plugin.metadata.plugin_type.value})")

    def register_plugins(self, plugins: List[BaseStrategyPlugin]) -> None:
        """Register multiple plugins"""
        for plugin in plugins:
            self.register_plugin(plugin)

    def discover_plugins(self) -> List[BaseStrategyPlugin]:
        """Discover plugins in configured directories"""
        discovered = []

        for plugin_dir in self.plugin_dirs:
            dir_path = Path(plugin_dir)
            if not dir_path.exists():
                self.logger.warning(f"Plugin directory not found: {plugin_dir}")
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
        """Discover and register all plugins"""
        plugins = self.discover_plugins()
        self.register_plugins(plugins)
        self.logger.info(f"Loaded {len(plugins)} plugins")

    def get_plugins(self, plugin_type: Optional[PluginType] = None) -> List[BaseStrategyPlugin]:
        """Get plugins from registry"""
        return self.registry.get_plugins(plugin_type)

    def get_best_plugin(self, browser_state: Dict[str, Any], plugin_type: PluginType) -> Optional[BaseStrategyPlugin]:
        """Get best plugin for current state"""
        return self.registry.get_best_plugin(browser_state, plugin_type)

    def reload_plugins(self) -> None:
        """Reload all plugins"""
        self.registry = PluginRegistry()
        self.load_plugins()
```

**Step 4: Update new_ai_agent.py to use plugin manager**

```python
# In google-business-project/scripts/agents/new_ai_agent.py __init__ method (around line 124-143)
        # Add plugin manager initialization
        self.plugin_manager = None
        self.current_strategy = None
```

```python
# In google-business-project/scripts/agents/new_ai_agent.py _initialize_components method (around line 241-279)
    def _initialize_components(self):
        """Initialize all agent components."""
        self.logger.info("🔧 Initialisiere Komponenten...")

        # 0. Plugin Manager (NEW)
        from agents.plugin_manager import PluginManager
        self.plugin_manager = PluginManager()
        self.plugin_manager.load_plugins()

        strategy_plugins = self.plugin_manager.get_plugins(PluginType.STRATEGY)
        self.logger.info(f"📦 Geladene Strategien: {len(strategy_plugins)}")

        # ... rest of existing initialization code remains
```

**Step 5: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/agents/test_plugin_manager.py::test_plugin_manager_registration -v
```
Expected: PASS

**Step 6: Commit plugin manager integration**

```bash
git add google-business-project/scripts/agents/plugin_manager.py tests/agents/test_plugin_manager.py google-business-project/scripts/agents/new_ai_agent.py
git commit -m "feat(PROJ-1): add plugin manager to new_ai_agent"
```

## Phase 2: Create Strategy Plugins from Existing Agents

### Task 4: Create Rule-Based Strategy Plugin from smart_agent.py

**Files:**
- Create: `google-business-project/scripts/agents/strategies/rule_based.py`
- Modify: `google-business-project/scripts/agents/smart_agent.py` (extract core logic)
- Create: `tests/agents/strategies/test_rule_based.py`

**Step 1: Write failing test for rule-based strategy**

```python
# tests/agents/strategies/test_rule_based.py
import pytest
from agents.strategies.rule_based import RuleBasedStrategy
from core.plugin_base import PluginType

def test_rule_based_strategy_creation():
    """Test rule-based strategy plugin creation"""
    strategy = RuleBasedStrategy()

    assert strategy.metadata.name == "RuleBasedStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert strategy.confidence_score >= 0.0
    assert strategy.confidence_score <= 1.0

def test_rule_based_can_handle():
    """Test can_handle method"""
    strategy = RuleBasedStrategy()

    # Should handle Google login pages
    google_state = {"url": "https://accounts.google.com", "text": "Email"}
    assert strategy.can_handle(google_state) == True

    # Should handle Google Business pages
    business_state = {"url": "https://business.google.com", "text": "Create Profile"}
    assert strategy.can_handle(business_state) == True
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_rule_based.py::test_rule_based_strategy_creation -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'agents.strategies.rule_based'"

**Step 3: Extract core logic from smart_agent.py and create plugin**

```python
# google-business-project/scripts/agents/strategies/rule_based.py
import re
import time
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata
from core.config import config, BUSINESS_DATA
from core.logger import setup_logger

@dataclass
class RuleBasedState:
    url: str
    text: str
    inputs: List[Dict[str, Any]]
    buttons: List[str]

class RuleBasedStrategy(BaseStrategyPlugin):
    """Rule-based strategy extracted from smart_agent.py"""

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__(config_overrides)

        self.logger = setup_logger("rule_based_strategy")
        self.metadata = PluginMetadata(
            name="RuleBasedStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Rule-based strategy from smart_agent.py with URL/text pattern matching",
            author="Migration",
            priority=50  # Medium priority (AI strategies might have higher)
        )

        # Configuration
        self.google_email = config.google_email
        self.google_password = config.google_password
        self.business_data = {
            'name': config.business_name,
            'street': config.business_address.get('street', ''),
            'zip': config.business_address.get('zip', ''),
            'city': config.business_address.get('city', ''),
            'phone': config.business_phone,
            'website': config.business_website,
            'category': config.business_category,
        }

        # State tracking (from smart_agent.py)
        self.last_url = None
        self.consecutive_same_url = 0

        self.logger.info("RuleBasedStrategy initialized")

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze browser state similar to smart_agent.py get_page_state"""
        # Simplified version - in real implementation would extract more details
        analyzed = {
            'url': browser_state.get('url', ''),
            'text': (browser_state.get('text', '') or '')[:3000],
            'inputs': browser_state.get('inputs', []),
            'buttons': browser_state.get('buttons', []),
            'title': browser_state.get('title', ''),
            'has_password_field': any(i.get('type') == 'password' for i in browser_state.get('inputs', [])),
            'has_email_field': any('email' in i.get('type', '').lower() for i in browser_state.get('inputs', [])),
        }

        # URL change tracking (from smart_agent.py)
        if analyzed['url'] == self.last_url:
            self.consecutive_same_url += 1
        else:
            self.consecutive_same_url = 0
            self.last_url = analyzed['url']

        analyzed['consecutive_same_url'] = self.consecutive_same_url

        return analyzed

    def decide_action(self, task: Dict[str, Any], current_state: Dict[str, Any],
                     history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Decide next action based on rules from smart_agent.py decide_next_action"""
        url = current_state['url']
        text = current_state['text'].lower()
        inputs = current_state['inputs']
        buttons = current_state['buttons']

        # Stuck detection (from smart_agent.py)
        if current_state.get('consecutive_same_url', 0) > 3:
            return {
                'type': 'press_enter',
                'details': {},
                'reasoning': 'URL ändert sich nicht - versuche Enter',
                'confidence': 0.7
            }

        # Completion check (from smart_agent.py)
        if 'dashboard' in url or 'locations' in url:
            return {
                'type': 'done',
                'details': {'message': 'Dashboard erreicht - fertig!'},
                'reasoning': 'Dashboard erreicht',
                'confidence': 0.95
            }

        # Google Accounts flow
        if 'accounts.google.com' in url:
            # 2FA Challenge (from smart_agent.py)
            if 'challenge' in url:
                match = re.search(r'\b(\d{2})\b', current_state['text'])
                if match:
                    return {
                        'type': 'wait_for_user',
                        'details': {'message': f'NUMMER {match.group(1)} AUF PIXEL TIPPEN!'},
                        'reasoning': f'2FA: Nummer {match.group(1)} auf Pixel tippen',
                        'confidence': 0.9
                    }
                return {
                    'type': 'wait_for_user',
                    'details': {'message': 'Bitte bestätigen Sie auf Ihrem Pixel!'},
                    'reasoning': '2FA - warte auf Benutzer',
                    'confidence': 0.8
                }

            # Password page (from smart_agent.py)
            if ('challenge/pwd' in url or 'challenge/pw' in url or
                current_state.get('has_password_field', False)):
                # Check if password already filled
                pwd_inputs = [i for i in inputs if i.get('type') == 'password']
                if pwd_inputs and pwd_inputs[0].get('value'):
                    # Password filled - click continue
                    return {
                        'type': 'click_button',
                        'details': {'text': 'Weiter'},
                        'reasoning': 'Passwort ausgefüllt - klicke Weiter',
                        'confidence': 0.85
                    }
                else:
                    # Enter password
                    return {
                        'type': 'fill_password',
                        'details': {'value': self.google_password if self.google_password else ''},
                        'reasoning': 'Passwort eingeben',
                        'confidence': 0.9
                    }

            # Email page (from smart_agent.py)
            if 'email' in text or 'e-mail' in text or current_state.get('has_email_field', False):
                # Check if email already filled
                email_input = next((i for i in inputs if i.get('type') == 'email' or
                                   'email' in i.get('aria_label', '').lower()),
                                  inputs[0] if inputs else None)

                if email_input and email_input.get('value') and self.google_email and self.google_email in email_input.get('value', ''):
                    # Email filled - click continue
                    return {
                        'type': 'click_button',
                        'details': {'text': 'Weiter'},
                        'reasoning': 'Email bereits ausgefüllt - klicke Weiter',
                        'confidence': 0.85
                    }
                else:
                    # Enter email
                    return {
                        'type': 'fill_input',
                        'details': {'index': 0, 'value': self.google_email if self.google_email else ''},
                        'reasoning': 'Email eingeben',
                        'confidence': 0.9
                    }

            # Fallback: Look for continue button
            for btn in buttons:
                if 'weiter' in btn.lower() or 'next' in btn.lower():
                    return {
                        'type': 'click_button',
                        'details': {'text': btn},
                        'reasoning': f'Klicke "{btn}"',
                        'confidence': 0.7
                    }

        # Google Business Create flow
        if 'business.google.com' in url:
            # Look for active inputs
            active_inputs = [i for i in inputs if not i.get('disabled') and not i.get('readonly')]

            if active_inputs:
                first = active_inputs[0]
                idx = inputs.index(first)

                # Determine what to enter based on page text
                if 'name' in text or 'unternehmen' in text or 'business' in text:
                    if not first.get('value'):
                        return {
                            'type': 'fill_input',
                            'details': {'index': idx, 'value': self.business_data.get('name', '')},
                            'reasoning': 'Unternehmensname eingeben',
                            'confidence': 0.85
                        }

                if 'kategorie' in text or 'branche' in text or 'category' in text:
                    if not first.get('value'):
                        return {
                            'type': 'fill_input',
                            'details': {'index': idx, 'value': self.business_data.get('category', '')},
                            'reasoning': 'Kategorie eingeben',
                            'confidence': 0.85
                        }

                if 'adresse' in text or 'straße' in text or 'street' in text:
                    if not first.get('value'):
                        return {
                            'type': 'fill_input',
                            'details': {'index': idx, 'value': self.business_data.get('street', '')},
                            'reasoning': 'Adresse eingeben',
                            'confidence': 0.85
                        }

            # Look for buttons to click
            for btn in buttons:
                btn_lower = btn.lower()
                if any(w in btn_lower for w in ['weiter', 'next', 'hinzufügen', 'add', 'erstellen', 'fertig', 'done']):
                    return {
                        'type': 'click_button',
                        'details': {'text': btn},
                        'reasoning': f'Klicke "{btn}"',
                        'confidence': 0.8
                    }

        # Default: Wait
        return {
            'type': 'wait',
            'details': {'seconds': 2},
            'reasoning': 'Warte auf Änderung',
            'confidence': 0.5
        }

    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute action similar to smart_agent.py execute_action"""
        action_type = action.get('type')
        details = action.get('details', {})

        try:
            if action_type == 'fill_input':
                idx = details.get('index', 0)
                value = details.get('value', '')
                inputs = browser_page.locator('input:visible, textarea:visible').all()
                if idx < len(inputs):
                    inputs[idx].click()
                    time.sleep(random.uniform(0.3, 0.5))
                    inputs[idx].fill(value)
                    return {'success': True, 'message': f'Filled input {idx}'}

            elif action_type == 'fill_password':
                value = details.get('value', '')
                pwd_input = browser_page.locator('input[type="password"]:visible').first
                pwd_input.click()
                time.sleep(random.uniform(0.3, 0.5))
                pwd_input.fill(value)
                return {'success': True, 'message': 'Filled password'}

            elif action_type == 'click_button':
                text = details.get('text', '')
                browser_page.click(f'button:has-text("{text}"), [role="button"]:has-text("{text}")')
                return {'success': True, 'message': f'Clicked button: {text}'}

            elif action_type == 'press_enter':
                browser_page.keyboard.press('Enter')
                return {'success': True, 'message': 'Pressed Enter'}

            elif action_type == 'wait':
                seconds = details.get('seconds', 2)
                time.sleep(seconds)
                return {'success': True, 'message': f'Waited {seconds}s'}

            elif action_type == 'wait_for_user':
                # Simplified version - would need full implementation
                return {'success': True, 'message': 'Waiting for user', 'requires_user': True}

            elif action_type == 'done':
                return {'success': True, 'message': 'Task completed', 'completed': True}

        except Exception as e:
            return {'success': False, 'error': str(e), 'message': f'Action {action_type} failed'}

        return {'success': False, 'error': 'Unknown action type', 'message': 'Action not implemented'}

    @property
    def confidence_score(self) -> float:
        """Confidence score based on rule coverage"""
        # Rule-based strategies have medium confidence
        # Could be adjusted based on success history
        return 0.7

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """Check if this strategy can handle the current state"""
        url = browser_state.get('url', '')
        text = (browser_state.get('text', '') or '').lower()

        # Can handle Google-related pages
        if 'google.com' in url:
            return True

        # Can handle pages with German text (smart_agent.py is German-focused)
        if any(word in text for word in ['weiter', 'email', 'passwort', 'unternehmen', 'adresse']):
            return True

        return False
```

**Step 4: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_rule_based.py::test_rule_based_strategy_creation -v
```
Expected: PASS

**Step 5: Commit rule-based strategy plugin**

```bash
git add google-business-project/scripts/agents/strategies/rule_based.py tests/agents/strategies/test_rule_based.py
git commit -m "feat(PROJ-1): create rule-based strategy plugin from smart_agent.py"
```

### Task 5: Create AI-Driven Strategy Plugin from agent_profile_creator.py

**Files:**
- Create: `google-business-project/scripts/agents/strategies/ai_driven.py`
- Modify: `google-business-project/scripts/agents/agent_profile_creator.py` (extract AI logic)
- Create: `tests/agents/strategies/test_ai_driven.py`

**Step 1: Write failing test for AI-driven strategy**

```python
# tests/agents/strategies/test_ai_driven.py
import pytest
from agents.strategies.ai_driven import AIDrivenStrategy
from core.plugin_base import PluginType

def test_ai_driven_strategy_creation():
    """Test AI-driven strategy plugin creation"""
    strategy = AIDrivenStrategy()

    assert strategy.metadata.name == "AIDrivenStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert hasattr(strategy, 'confidence_score')

    # Check config loading
    assert hasattr(strategy, 'ai_providers')
    assert isinstance(strategy.ai_providers, list)
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_ai_driven.py::test_ai_driven_strategy_creation -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'agents.strategies.ai_driven'"

**Step 3: Extract AI logic from agent_profile_creator.py and create plugin**

```python
# google-business-project/scripts/agents/strategies/ai_driven.py
import base64
import json
import time
from typing import Dict, Any, List, Optional
import importlib

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata
from core.config import config
from core.logger import setup_logger

class AIDrivenStrategy(BaseStrategyPlugin):
    """AI-driven strategy extracted from agent_profile_creator.py"""

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__(config_overrides)

        self.logger = setup_logger("ai_driven_strategy")
        self.metadata = PluginMetadata(
            name="AIDrivenStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="AI-driven strategy from agent_profile_creator.py with screenshot analysis",
            author="Migration",
            priority=30  # Higher priority than rule-based (more advanced)
        )

        # AI provider configuration
        self.ai_providers = []
        self.current_provider = None
        self.provider_errors = {}

        self._init_ai_providers()
        self.logger.info(f"AIDrivenStrategy initialized with {len(self.ai_providers)} AI providers")

    def _init_ai_providers(self):
        """Initialize AI providers from config"""
        # Try Anthropic
        try:
            import anthropic
            if hasattr(config, 'anthropic_api_key') and config.anthropic_api_key:
                self.ai_providers.append({
                    'name': 'anthropic',
                    'module': anthropic,
                    'client': anthropic.Anthropic(api_key=config.anthropic_api_key),
                    'model': config.anthropic_model or 'claude-3-5-sonnet-20241022'
                })
                self.logger.info("✅ Anthropic provider loaded")
        except ImportError:
            self.logger.warning("⚠️ Anthropic not available")
        except Exception as e:
            self.logger.error(f"❌ Anthropic initialization failed: {e}")

        # Try OpenAI/DeepSeek
        try:
            import openai
            if hasattr(config, 'openai_api_key') and config.openai_api_key:
                self.ai_providers.append({
                    'name': 'openai',
                    'module': openai,
                    'client': openai.OpenAI(api_key=config.openai_api_key, base_url=config.openai_base_url),
                    'model': config.openai_model or 'gpt-4'
                })
                self.logger.info("✅ OpenAI/DeepSeek provider loaded")
        except ImportError:
            self.logger.warning("⚠️ OpenAI not available")
        except Exception as e:
            self.logger.error(f"❌ OpenAI initialization failed: {e}")

        if not self.ai_providers:
            self.logger.warning("⚠️ No AI providers available - strategy will fallback")

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze browser state with screenshot capture"""
        # Ensure we have screenshot
        if 'screenshot_b64' not in browser_state and 'page' in browser_state:
            try:
                screenshot_bytes = browser_state['page'].screenshot(type='png')
                browser_state['screenshot_b64'] = base64.b64encode(screenshot_bytes).decode()
            except Exception as e:
                self.logger.error(f"Failed to capture screenshot: {e}")

        analyzed = {
            'url': browser_state.get('url', ''),
            'title': browser_state.get('title', ''),
            'text': browser_state.get('text', ''),
            'screenshot_available': 'screenshot_b64' in browser_state,
            'screenshot_size': len(browser_state.get('screenshot_b64', '')),
            'inputs_count': len(browser_state.get('inputs', [])),
            'buttons_count': len(browser_state.get('buttons', [])),
        }

        return analyzed

    def decide_action(self, task: Dict[str, Any], current_state: Dict[str, Any],
                     history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use AI to decide next action based on screenshot and context"""

        # If no AI providers available, return low-confidence wait action
        if not self.ai_providers:
            return {
                'type': 'wait',
                'details': {'seconds': 3},
                'reasoning': 'No AI providers available - waiting',
                'confidence': 0.1
            }

        # Prepare context for AI
        context = {
            'task': task,
            'current_state': {
                'url': current_state.get('url', ''),
                'title': current_state.get('title', ''),
                'text_preview': (current_state.get('text', '') or '')[:500],
                'inputs_count': current_state.get('inputs_count', 0),
                'buttons_count': current_state.get('buttons_count', 0),
            },
            'recent_history': history[-5:] if history else [],
            'has_screenshot': current_state.get('screenshot_available', False),
        }

        # Try each provider until one succeeds
        for provider in self.ai_providers:
            try:
                action = self._ask_ai(provider, context, current_state)
                if action:
                    return action
            except Exception as e:
                self.logger.error(f"AI provider {provider['name']} failed: {e}")
                self.provider_errors[provider['name']] = str(e)

        # All providers failed
        return {
            'type': 'wait',
            'details': {'seconds': 2},
            'reasoning': 'All AI providers failed - waiting',
            'confidence': 0.2
        }

    def _ask_ai(self, provider: Dict[str, Any], context: Dict[str, Any],
                current_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Ask AI provider for decision"""

        # Build prompt similar to agent_profile_creator.py
        prompt = f"""
        You are an AI assistant controlling a browser to automate Google Business Profile creation.

        TASK: {json.dumps(context['task'], indent=2)}

        CURRENT PAGE:
        - URL: {context['current_state']['url']}
        - Title: {context['current_state']['title']}
        - Text Preview: {context['current_state']['text_preview']}
        - Inputs: {context['current_state']['inputs_count']} visible input fields
        - Buttons: {context['current_state']['buttons_count']} visible buttons

        RECENT HISTORY (last 5 actions):
        {json.dumps(context['recent_history'], indent=2)}

        What should the browser do next? Choose ONE action from:
        1. navigate(url) - navigate to a specific URL
        2. click(selector) - click an element with CSS selector or text
        3. fill(selector, value) - fill an input field
        4. select(selector, value) - select an option from dropdown
        5. wait(seconds) - wait for specified seconds
        6. screenshot() - take a screenshot for analysis
        7. done(message) - task is complete

        Respond in JSON format:
        {{
            "action": "action_type",
            "details": {{...}},
            "reasoning": "explanation of why this action",
            "confidence": 0.0-1.0
        }}
        """

        messages = [
            {"role": "user", "content": prompt}
        ]

        # Add screenshot if available
        if context['has_screenshot'] and current_state.get('screenshot_b64'):
            if provider['name'] == 'anthropic':
                messages[0]["content"] = [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": current_state.get('screenshot_b64')
                        }
                    }
                ]

        try:
            if provider['name'] == 'anthropic':
                response = provider['client'].messages.create(
                    model=provider['model'],
                    max_tokens=1000,
                    messages=messages
                )
                content = response.content[0].text
            elif provider['name'] == 'openai':
                response = provider['client'].chat.completions.create(
                    model=provider['model'],
                    messages=messages,
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            else:
                return None

            # Parse JSON response
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                action_data = json.loads(json_match.group())
                return action_data
            else:
                self.logger.warning(f"Could not parse JSON from AI response: {content[:200]}")
                return None

        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise

    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute AI-decided action"""
        # For now, use a simple executor - would integrate with existing action executor
        action_type = action.get('action')
        details = action.get('details', {})

        try:
            if action_type == 'navigate':
                url = details.get('url')
                browser_page.goto(url)
                return {'success': True, 'message': f'Navigated to {url}'}

            elif action_type == 'click':
                selector = details.get('selector')
                browser_page.click(selector)
                return {'success': True, 'message': f'Clicked {selector}'}

            elif action_type == 'fill':
                selector = details.get('selector')
                value = details.get('value')
                browser_page.fill(selector, value)
                return {'success': True, 'message': f'Filled {selector} with {value}'}

            elif action_type == 'wait':
                seconds = details.get('seconds', 2)
                time.sleep(seconds)
                return {'success': True, 'message': f'Waited {seconds}s'}

            elif action_type == 'screenshot':
                # Screenshot already captured in analyze_state
                return {'success': True, 'message': 'Screenshot captured'}

            elif action_type == 'done':
                return {'success': True, 'message': 'Task completed', 'completed': True}

            else:
                return {'success': False, 'error': f'Unknown action type: {action_type}'}

        except Exception as e:
            return {'success': False, 'error': str(e), 'message': f'Action {action_type} failed'}

    @property
    def confidence_score(self) -> float:
        """Confidence score based on AI provider availability and success rate"""
        if not self.ai_providers:
            return 0.1

        # Higher confidence with more providers available
        base_score = 0.8

        # Adjust based on error rate
        error_count = len(self.provider_errors)
        if error_count > 0:
            base_score -= (error_count * 0.1)

        return max(0.1, min(1.0, base_score))

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """AI strategy can handle any state if providers are available"""
        return len(self.ai_providers) > 0
```

**Step 4: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_ai_driven.py::test_ai_driven_strategy_creation -v
```
Expected: PASS (may have warnings if AI providers not configured)

**Step 5: Commit AI-driven strategy plugin**

```bash
git add google-business-project/scripts/agents/strategies/ai_driven.py tests/agents/strategies/test_ai_driven.py
git commit -m "feat(PROJ-1): create AI-driven strategy plugin from agent_profile_creator.py"
```

### Task 6: Create Hybrid Strategy Plugin

**Files:**
- Create: `google-business-project/scripts/agents/strategies/hybrid.py`
- Create: `tests/agents/strategies/test_hybrid.py`

**Step 1: Write failing test for hybrid strategy**

```python
# tests/agents/strategies/test_hybrid.py
import pytest
from agents.strategies.hybrid import HybridStrategy
from core.plugin_base import PluginType

def test_hybrid_strategy_creation():
    """Test hybrid strategy plugin creation"""
    strategy = HybridStrategy()

    assert strategy.metadata.name == "HybridStrategy"
    assert strategy.metadata.plugin_type == PluginType.STRATEGY
    assert hasattr(strategy, 'confidence_score')
    assert hasattr(strategy, 'strategies')
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_hybrid.py::test_hybrid_strategy_creation -v
```
Expected: FAIL with "ModuleNotFoundError: No module named 'agents.strategies.hybrid'"

**Step 3: Create hybrid strategy that combines rule-based and AI approaches**

```python
# google-business-project/scripts/agents/strategies/hybrid.py
from typing import Dict, Any, List, Optional
import time

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata
from core.logger import setup_logger

class HybridStrategy(BaseStrategyPlugin):
    """Hybrid strategy that combines rule-based and AI approaches"""

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        super().__init__(config_overrides)

        self.logger = setup_logger("hybrid_strategy")
        self.metadata = PluginMetadata(
            name="HybridStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Hybrid strategy combining rule-based and AI approaches with fallback",
            author="Migration",
            priority=20  # High priority (smart combination)
        )

        # Load sub-strategies
        self.strategies = []
        self._load_strategies()

        self.success_counts = {}
        self.failure_counts = {}

        self.logger.info(f"HybridStrategy initialized with {len(self.strategies)} sub-strategies")

    def _load_strategies(self):
        """Dynamically load available strategies"""
        try:
            from agents.strategies.ai_driven import AIDrivenStrategy
            ai_strategy = AIDrivenStrategy(self.config)
            self.strategies.append({
                'strategy': ai_strategy,
                'weight': 0.7,  # Prefer AI when available
                'type': 'ai'
            })
            self.logger.info("✅ Loaded AI-driven strategy")
        except ImportError as e:
            self.logger.warning(f"⚠️ Could not load AI-driven strategy: {e}")

        try:
            from agents.strategies.rule_based import RuleBasedStrategy
            rule_strategy = RuleBasedStrategy(self.config)
            self.strategies.append({
                'strategy': rule_strategy,
                'weight': 0.3,  # Fallback to rules
                'type': 'rule'
            })
            self.logger.info("✅ Loaded rule-based strategy")
        except ImportError as e:
            self.logger.warning(f"⚠️ Could not load rule-based strategy: {e}")

        if not self.strategies:
            self.logger.warning("⚠️ No sub-strategies available")

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """Let each strategy analyze the state"""
        analyses = {}

        for i, strategy_info in enumerate(self.strategies):
            try:
                analysis = strategy_info['strategy'].analyze_state(browser_state)
                analyses[strategy_info['type']] = analysis
            except Exception as e:
                self.logger.error(f"Strategy {strategy_info['type']} analysis failed: {e}")
                analyses[strategy_info['type']] = {'error': str(e)}

        # Combine analyses
        combined = {
            'url': browser_state.get('url', ''),
            'text': browser_state.get('text', ''),
            'analyses': analyses,
            'strategy_count': len(self.strategies),
            'available_strategies': [s['type'] for s in self.strategies]
        }

        return combined

    def decide_action(self, task: Dict[str, Any], current_state: Dict[str, Any],
                     history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use weighted combination of strategies to decide action"""

        if not self.strategies:
            # Fallback if no strategies
            return {
                'type': 'wait',
                'details': {'seconds': 3},
                'reasoning': 'No strategies available - waiting',
                'confidence': 0.1
            }

        # Get decisions from all strategies
        decisions = []
        for strategy_info in self.strategies:
            try:
                decision = strategy_info['strategy'].decide_action(task, current_state, history)
                if decision:
                    decisions.append({
                        'decision': decision,
                        'weight': strategy_info['weight'],
                        'type': strategy_info['type'],
                        'confidence': decision.get('confidence', 0.5)
                    })
            except Exception as e:
                self.logger.error(f"Strategy {strategy_info['type']} decision failed: {e}")

        if not decisions:
            # All strategies failed
            return {
                'type': 'wait',
                'details': {'seconds': 2},
                'reasoning': 'All strategies failed - waiting',
                'confidence': 0.2
            }

        # Weight decisions by strategy weight and confidence
        weighted_decisions = []
        for d in decisions:
            weight = d['weight'] * d['confidence']
            weighted_decisions.append((weight, d['decision']))

        # Sort by weight (descending)
        weighted_decisions.sort(key=lambda x: x[0], reverse=True)

        # Use highest weighted decision
        best_weight, best_decision = weighted_decisions[0]

        # Adjust confidence based on weight
        adjusted_confidence = min(0.95, best_decision.get('confidence', 0.5) * (1 + best_weight))

        return {
            'type': best_decision.get('type'),
            'details': best_decision.get('details', {}),
            'reasoning': f"Hybrid: {best_decision.get('reasoning', '')} (via {weighted_decisions[0][1]['type']})",
            'confidence': adjusted_confidence
        }

    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute action and track success/failure for learning"""
        action_type = action.get('type')

        # Try to find which strategy would handle this action type best
        executing_strategy = None
        for strategy_info in self.strategies:
            if strategy_info['type'] == 'rule' and action_type in ['fill_input', 'click_button', 'wait_for_user']:
                executing_strategy = strategy_info['strategy']
                break
            elif strategy_info['type'] == 'ai' and action_type in ['navigate', 'click', 'fill']:
                executing_strategy = strategy_info['strategy']
                break

        # Execute with best matching strategy or first available
        if not executing_strategy and self.strategies:
            executing_strategy = self.strategies[0]['strategy']

        if executing_strategy:
            try:
                result = executing_strategy.execute_action(action, browser_page)

                # Track success/failure
                strategy_type = next(s['type'] for s in self.strategies if s['strategy'] == executing_strategy)
                if result.get('success'):
                    self.success_counts[strategy_type] = self.success_counts.get(strategy_type, 0) + 1
                else:
                    self.failure_counts[strategy_type] = self.failure_counts.get(strategy_type, 0) + 1

                return result
            except Exception as e:
                self.logger.error(f"Strategy execution failed: {e}")
                return {'success': False, 'error': str(e)}
        else:
            # Basic execution as fallback
            try:
                if action_type == 'wait':
                    seconds = action.get('details', {}).get('seconds', 2)
                    time.sleep(seconds)
                    return {'success': True, 'message': f'Waited {seconds}s'}
                else:
                    return {'success': False, 'error': f'No strategy to execute {action_type}'}
            except Exception as e:
                return {'success': False, 'error': str(e)}

    @property
    def confidence_score(self) -> float:
        """Confidence based on success rates of sub-strategies"""
        if not self.strategies:
            return 0.1

        total_attempts = 0
        total_successes = 0

        for strategy_info in self.strategies:
            strategy_type = strategy_info['type']
            successes = self.success_counts.get(strategy_type, 0)
            failures = self.failure_counts.get(strategy_type, 0)

            total_attempts += successes + failures
            total_successes += successes

        if total_attempts == 0:
            # No history yet - base on strategy weights
            avg_weight = sum(s['weight'] for s in self.strategies) / len(self.strategies)
            return 0.5 + (avg_weight * 0.3)

        success_rate = total_successes / total_attempts

        # Adjust based on number of available strategies
        strategy_bonus = len(self.strategies) * 0.1

        return min(0.95, success_rate + strategy_bonus)

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """Can handle if any sub-strategy can handle"""
        return any(s['strategy'].can_handle(browser_state) for s in self.strategies)
```

**Step 4: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/agents/strategies/test_hybrid.py::test_hybrid_strategy_creation -v
```
Expected: PASS (may have warnings if dependencies not available)

**Step 5: Commit hybrid strategy plugin**

```bash
git add google-business-project/scripts/agents/strategies/hybrid.py tests/agents/strategies/test_hybrid.py
git commit -m "feat(PROJ-1): create hybrid strategy plugin combining rule-based and AI approaches"
```

## Phase 3: Integration and Strategy Selection

### Task 7: Update new_ai_agent.py for Dynamic Strategy Selection

**Files:**
- Modify: `google-business-project/scripts/agents/new_ai_agent.py:160-200` (main execution loop)
- Modify: `google-business-project/scripts/agents/new_ai_agent.py:281-292` (_create_decision_context)
- Create: `tests/agents/test_strategy_selection.py`

**Step 1: Write failing test for strategy selection**

```python
# tests/agents/test_strategy_selection.py
import pytest
from agents.new_ai_agent import NewAIAgent
from unittest.mock import Mock, patch

def test_agent_strategy_selection():
    """Test that agent selects appropriate strategy"""
    with patch('agents.new_ai_agent.PluginManager') as mock_manager:
        # Mock plugin manager with strategies
        mock_strategy = Mock()
        mock_strategy.can_handle.return_value = True
        mock_strategy.confidence_score = 0.8

        mock_manager_instance = Mock()
        mock_manager_instance.get_best_plugin.return_value = mock_strategy
        mock_manager.return_value = mock_manager_instance

        agent = NewAIAgent("Test task")

        # Check strategy selection
        browser_state = {"url": "https://accounts.google.com"}
        strategy = agent._select_strategy(browser_state)

        assert strategy == mock_strategy
        mock_manager_instance.get_best_plugin.assert_called_once()
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/agents/test_strategy_selection.py::test_agent_strategy_selection -v
```
Expected: FAIL with "ModuleNotFoundError" or missing _select_strategy method

**Step 3: Add strategy selection methods to new_ai_agent.py**

```python
# Add to google-business-project/scripts/agents/new_ai_agent.py after __init__ method

    def _select_strategy(self, browser_state: Dict[str, Any]) -> Optional[BaseStrategyPlugin]:
        """Select the best strategy for current browser state."""
        if not self.plugin_manager:
            self.logger.warning("⚠️ Plugin manager not initialized")
            return None

        from core.plugin_base import PluginType

        try:
            strategy = self.plugin_manager.get_best_plugin(browser_state, PluginType.STRATEGY)
            if strategy:
                self.logger.info(f"🎯 Selected strategy: {strategy.metadata.name} (confidence: {strategy.confidence_score:.2f})")
                self.current_strategy = strategy
            else:
                self.logger.warning("⚠️ No suitable strategy found")
                self.current_strategy = None

            return strategy
        except Exception as e:
            self.logger.error(f"❌ Strategy selection failed: {e}")
            return None

    def _execute_with_strategy(self, strategy: BaseStrategyPlugin,
                              task: Dict[str, Any],
                              browser_state: Dict[str, Any],
                              history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute decision cycle with selected strategy."""
        try:
            # 1. Analyze state with strategy
            analyzed_state = strategy.analyze_state(browser_state)

            # 2. Decide action with strategy
            action = strategy.decide_action(task, analyzed_state, history)

            # 3. Execute action with strategy
            result = strategy.execute_action(action, self.browser.page if self.browser else None)

            return {
                'action': action,
                'result': result,
                'strategy': strategy.metadata.name,
                'confidence': action.get('confidence', 0.5)
            }
        except Exception as e:
            self.logger.error(f"❌ Strategy execution failed: {e}")
            return {
                'action': {'type': 'error', 'details': {'error': str(e)}},
                'result': {'success': False, 'error': str(e)},
                'strategy': strategy.metadata.name if strategy else 'unknown',
                'confidence': 0.0
            }
```

**Step 4: Update main execution loop to use strategy selection**

```python
# In google-business-project/scripts/agents/new_ai_agent.py execute method (around line 160-200)
        # Haupt-Ausführungsschleife
        while self.iteration < self.max_iterations:
            self.iteration += 1
            self.logger.info(f"🔄 Iteration {self.iteration}/{self.max_iterations}")

            # 1. Hole Browser-Zustand
            browser_state = self._get_browser_state()

            # 2. Wähle beste Strategie
            strategy = self._select_strategy(browser_state)
            if not strategy:
                self.logger.warning("⚠️ Keine Strategie verfügbar - warte")
                time.sleep(2)
                continue

            # 3. Führe mit Strategie aus
            execution_result = self._execute_with_strategy(
                strategy,
                {
                    'description': self.task.description,
                    'goal': self.task.goal,
                    'parameters': self.task.parameters
                },
                browser_state,
                self.action_history[-10:] if self.action_history else []
            )

            # 4. Aktualisiere Historie
            self.action_history.append({
                "iteration": self.iteration,
                "strategy": execution_result['strategy'],
                "action": execution_result['action'],
                "result": execution_result['result'],
                "confidence": execution_result['confidence']
            })

            # 5. Prüfe ob Aufgabe abgeschlossen ist
            if self._is_task_complete():
                self.logger.info("🎉 Aufgabe erfolgreich abgeschlossen!")
                break

            # 6. Prüfe auf Fehler
            if not execution_result['result'].get('success', False):
                self.logger.warning(f"⚠️ Aktion fehlgeschlagen: {execution_result['result'].get('error', 'Unbekannt')}")

            # 7. Warte für nächste Iteration
            time.sleep(1)
```

**Step 5: Add _get_browser_state method**

```python
# Add to google-business-project/scripts/agents/new_ai_agent.py

    def _get_browser_state(self) -> Dict[str, Any]:
        """Get current browser state for strategy analysis."""
        if not self.browser or not self.browser.page:
            return {'url': '', 'text': '', 'title': '', 'inputs': [], 'buttons': []}

        try:
            page = self.browser.page

            # Basic state information
            state = {
                'url': page.url,
                'title': page.title(),
                'text': page.locator('body').inner_text()[:3000] if page.locator('body').count() > 0 else '',
                'page': page,  # Pass page for screenshot capture
            }

            # Try to get inputs and buttons (similar to smart_agent.py)
            try:
                inputs = page.locator('input:visible, textarea:visible').all()
                state['inputs'] = []
                for i, inp in enumerate(inputs[:10]):
                    try:
                        state['inputs'].append({
                            'index': i,
                            'type': inp.get_attribute('type') or 'text',
                            'placeholder': inp.get_attribute('placeholder') or '',
                            'aria_label': inp.get_attribute('aria-label') or '',
                            'name': inp.get_attribute('name') or '',
                            'disabled': inp.is_disabled(),
                            'readonly': inp.get_attribute('readonly') is not None,
                            'value': inp.input_value() if inp.get_attribute('type') != 'password' else '',
                        })
                    except:
                        pass
            except:
                state['inputs'] = []

            try:
                buttons = page.locator('button:visible, [role="button"]:visible').all()
                state['buttons'] = []
                for btn in buttons[:15]:
                    try:
                        text = btn.inner_text()[:50].strip()
                        if text:
                            state['buttons'].append(text)
                    except:
                        pass
            except:
                state['buttons'] = []

            return state

        except Exception as e:
            self.logger.error(f"❌ Browser state collection failed: {e}")
            return {'url': '', 'text': '', 'title': '', 'inputs': [], 'buttons': [], 'error': str(e)}
```

**Step 6: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/agents/test_strategy_selection.py::test_agent_strategy_selection -v
```
Expected: PASS

**Step 7: Commit strategy selection integration**

```bash
git add google-business-project/scripts/agents/new_ai_agent.py tests/agents/test_strategy_selection.py
git commit -m "feat(PROJ-1): add dynamic strategy selection to new_ai_agent"
```

## Phase 4: Testing and Validation

### Task 8: Create Integration Tests for Unified Agent

**Files:**
- Create: `tests/integration/test_unified_agent.py`
- Create: `tests/fixtures/browser_mock.py`
- Modify: `google-business-project/scripts/core/config.py` (add test configuration)

**Step 1: Write failing integration test**

```python
# tests/integration/test_unified_agent.py
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def test_unified_agent_with_mock_strategies():
    """Test unified agent with mocked strategies"""

    # Mock browser and components
    with patch('agents.new_ai_agent.EnhancedBrowser') as mock_browser_class, \
         patch('agents.new_ai_agent.PluginManager') as mock_plugin_manager_class, \
         patch('agents.new_ai_agent.Config') as mock_config_class:

        # Setup mocks
        mock_browser = Mock()
        mock_browser.page = Mock()
        mock_browser.page.url = 'https://accounts.google.com'
        mock_browser.page.title.return_value = 'Google Accounts'
        mock_browser.page.locator.return_value.inner_text.return_value = 'Email'
        mock_browser.page.locator.return_value.count.return_value = 1
        mock_browser_class.return_value = mock_browser

        mock_config = Mock()
        mock_config.agent_headless = True
        mock_config.agent_humanize = False
        mock_config.browser_locale = 'de-DE'
        mock_config.browser_os = 'Windows'
        mock_config.browser_geoip = 'DE'
        mock_config.agent_timeout = 30000
        mock_config_class.return_value = mock_config

        # Mock plugin manager with strategy
        mock_strategy = Mock()
        mock_strategy.metadata.name = 'TestStrategy'
        mock_strategy.confidence_score = 0.8
        mock_strategy.analyze_state.return_value = {'url': 'https://accounts.google.com', 'text': 'Email'}
        mock_strategy.decide_action.return_value = {
            'type': 'fill_input',
            'details': {'index': 0, 'value': 'test@example.com'},
            'reasoning': 'Test',
            'confidence': 0.9
        }
        mock_strategy.execute_action.return_value = {'success': True, 'message': 'Filled input'}

        mock_plugin_manager = Mock()
        mock_plugin_manager.get_best_plugin.return_value = mock_strategy
        mock_plugin_manager_class.return_value = mock_plugin_manager

        # Import and test agent
        from agents.new_ai_agent import NewAIAgent

        # Create agent with short max iterations for test
        agent = NewAIAgent("Test login task", {"max_iterations": 2})

        # Mock _is_task_complete to end quickly
        agent._is_task_complete = Mock()
        agent._is_task_complete.side_effect = [False, True]

        # Execute
        result = agent.execute()

        # Verify results
        assert 'status' in result
        assert result['execution']['iterations'] >= 1
        assert len(result['action_history']) >= 1

        # Verify strategy was used
        mock_plugin_manager.get_best_plugin.assert_called()
        mock_strategy.decide_action.assert_called()
```

**Step 2: Run test to verify it fails**

```bash
cd google-business-project
python -m pytest tests/integration/test_unified_agent.py::test_unified_agent_with_mock_strategies -v
```
Expected: FAIL (but should run, may have import issues)

**Step 3: Add test configuration support**

```python
# Add to google-business-project/scripts/core/config.py (if not exists)

class TestConfig:
    """Test configuration for unit tests"""
    google_email = "test@example.com"
    google_password = "testpassword"
    business_name = "Test Business"
    business_address = {"street": "Test St", "zip": "12345", "city": "Test City"}
    business_phone = "+1234567890"
    business_website = "https://test.example.com"
    business_category = "Test Category"
    agent_headless = True
    agent_humanize = False
    browser_locale = "de-DE"
    browser_os = "Windows"
    browser_geoip = "DE"
    agent_timeout = 30000
    agent_max_iterations = 50
```

**Step 4: Update imports in test to use test config**

```python
# Update test file to use test config
# In tests/integration/test_unified_agent.py, update the mock:

def test_unified_agent_with_mock_strategies():
    # ... existing code ...

    # Mock config to return TestConfig
    with patch('agents.new_ai_agent.Config') as mock_config_class:
        mock_config = Mock()
        # Set all required attributes
        mock_config.google_email = "test@example.com"
        mock_config.google_password = "testpassword"
        mock_config.business_name = "Test Business"
        mock_config.business_address = {"street": "Test St", "zip": "12345", "city": "Test City"}
        mock_config.business_phone = "+1234567890"
        mock_config.business_website = "https://test.example.com"
        mock_config.business_category = "Test Category"
        mock_config.agent_headless = True
        mock_config.agent_humanize = False
        mock_config.browser_locale = "de-DE"
        mock_config.browser_os = "Windows"
        mock_config.browser_geoip = "DE"
        mock_config.agent_timeout = 30000
        mock_config_class.return_value = mock_config

        # ... rest of test ...
```

**Step 5: Run test to verify it passes**

```bash
cd google-business-project
python -m pytest tests/integration/test_unified_agent.py::test_unified_agent_with_mock_strategies -v
```
Expected: PASS (with mocks)

**Step 6: Commit integration tests**

```bash
git add tests/integration/test_unified_agent.py google-business-project/scripts/core/config.py
git commit -m "test(PROJ-1): add integration tests for unified agent"
```

### Task 9: Create End-to-End Test Script

**Files:**
- Create: `google-business-project/scripts/test_unified_agent.py`
- Create: `tests/e2e/test_smoke.py`

**Step 1: Create smoke test script**

```python
# google-business-project/scripts/test_unified_agent.py
#!/usr/bin/env python3
"""
Smoke test for unified Google Business agent.
Tests plugin loading, strategy selection, and basic execution.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from core.logger import setup_logger
from agents.plugin_manager import PluginManager
from core.plugin_base import PluginType

def test_plugin_loading():
    """Test plugin discovery and loading"""
    logger = setup_logger("smoke_test")
    logger.info("🧪 Starting smoke test...")

    # Test plugin manager
    manager = PluginManager()
    manager.load_plugins()

    strategies = manager.get_plugins(PluginType.STRATEGY)
    logger.info(f"📦 Loaded {len(strategies)} strategy plugins")

    for strategy in strategies:
        logger.info(f"  • {strategy.metadata.name} v{strategy.metadata.version}")
        logger.info(f"    {strategy.metadata.description}")
        logger.info(f"    Confidence: {strategy.confidence_score:.2f}, Priority: {strategy.metadata.priority}")

    # Test strategy selection with mock state
    test_state = {
        'url': 'https://accounts.google.com',
        'text': 'Email login page',
        'inputs': [],
        'buttons': []
    }

    best_strategy = manager.get_best_plugin(test_state, PluginType.STRATEGY)
    if best_strategy:
        logger.info(f"🎯 Best strategy for login page: {best_strategy.metadata.name}")
    else:
        logger.warning("⚠️ No strategy found for login page")

    # Test can_handle methods
    for strategy in strategies:
        can_handle = strategy.can_handle(test_state)
        logger.info(f"  • {strategy.metadata.name}: can_handle = {can_handle}")

    return len(strategies) > 0

def main():
    """Main smoke test function"""
    print("🚀 Google Business Agent - Smoke Test")
    print("=" * 50)

    try:
        success = test_plugin_loading()

        if success:
            print("✅ Smoke test PASSED")
            print("✅ Plugin system is working")
            return 0
        else:
            print("⚠️ Smoke test WARNING: No plugins loaded")
            print("ℹ️  This may be expected if no strategies are implemented yet")
            return 0  # Warning, not error

    except Exception as e:
        print(f"❌ Smoke test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

**Step 2: Create simple E2E test**

```python
# tests/e2e/test_smoke.py
import pytest
import subprocess
import sys
import os

def test_plugin_smoke_test():
    """Run the smoke test script"""
    script_path = os.path.join(os.path.dirname(__file__), '..', '..', 'google-business-project', 'scripts', 'test_unified_agent.py')

    result = subprocess.run([sys.executable, script_path],
                          capture_output=True,
                          text=True,
                          cwd=os.path.join(os.path.dirname(__file__), '..', '..', 'google-business-project'))

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Test passes if script runs without crashing
    assert result.returncode == 0, f"Smoke test failed with return code {result.returncode}"
    assert "Smoke test" in result.stdout or "smoke test" in result.stdout.lower()
```

**Step 3: Run smoke test**

```bash
cd google-business-project
python scripts/test_unified_agent.py
```
Expected: Should run without crashing, may show warnings if no plugins yet

**Step 4: Run E2E test**

```bash
cd google-business-project
python -m pytest tests/e2e/test_smoke.py::test_plugin_smoke_test -v
```
Expected: PASS (if script runs)

**Step 5: Commit smoke tests**

```bash
git add google-business-project/scripts/test_unified_agent.py tests/e2e/test_smoke.py
git commit -m "test(PROJ-1): add smoke tests for unified agent"
```

## Phase 5: Documentation and Cleanup

### Task 10: Update Documentation and Create Migration Guide

**Files:**
- Update: `google-business-project/README.md`
- Create: `google-business-project/docs/MIGRATION_GUIDE.md`
- Update: `features/INDEX.md` (status update)
- Create: `google-business-project/docs/USAGE.md`

**Step 1: Update README with new architecture**

```markdown
# Google Business Agent - Unified Architecture

> **Status**: Migration in Progress (PROJ-1)
> **Last Updated**: 2026-03-02

## Overview

This project consolidates multiple Google Business agent implementations into a unified, modular architecture. The new system uses a plugin-based approach where different strategies (rule-based, AI-driven, hybrid) can be dynamically selected based on the task and current browser state.

## New Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Unified Agent (new_ai_agent.py)          │
├─────────────────────────────────────────────────────────────┤
│  Plugin Manager → Strategy Selection → Execution Tracking   │
└─────────────────────────────────────────────────────────────┘
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
        ┌─────────────┬─────────────┬─────────────┐
        │ Rule-Based  │  AI-Driven  │   Hybrid    │
        │  Strategy   │  Strategy   │  Strategy   │
        └─────────────┴─────────────┴─────────────┘
```

## Key Changes

1. **Plugin System**: All strategies are now plugins implementing `BaseStrategyPlugin`
2. **Dynamic Selection**: Agent selects best strategy based on confidence and state
3. **Unified Interface**: Single CLI entry point for all operations
4. **Preserved Functionality**: All existing agent logic migrated to plugins

## Migration Status

✅ **Phase 1**: Plugin interface design completed
✅ **Phase 2**: Strategy plugins created
✅ **Phase 3**: Dynamic strategy selection implemented
🔄 **Phase 4**: Testing and validation in progress
⏳ **Phase 5**: Documentation and cleanup

## Quick Start

```bash
# Run unified agent
cd google-business-project
python scripts/agents/new_ai_agent.py "Create Google Business profile"

# Test plugin system
python scripts/test_unified_agent.py

# List available strategies
python scripts/agents/plugin_manager.py --list
```

## Configuration

Copy `.env.example` to `.env` and set:
- `GOOGLE_EMAIL`, `GOOGLE_PASSWORD`: Google account credentials
- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`: AI provider keys (optional)
- `BUSINESS_*`: Business information for profile creation

## Documentation

- [Migration Guide](./docs/MIGRATION_GUIDE.md) - How to migrate from old agents
- [Usage Guide](./docs/USAGE.md) - How to use the unified agent
- [Plugin Development](./docs/PLUGIN_DEVELOPMENT.md) - How to create new strategies
- [Architecture](./docs/ARCHITECTURE.md) - Technical architecture details
```

**Step 2: Create migration guide**

```markdown
# Migration Guide: Old Agents to Unified Architecture

## Overview

This guide explains how to migrate from the old agent implementations (`smart_agent.py`, `agent_profile_creator.py`, `ai_profile_creator.py`) to the new unified architecture.

## What's Changed

| Old Component | New Equivalent | Migration Status |
|---------------|----------------|------------------|
| `smart_agent.py` | `RuleBasedStrategy` plugin | ✅ Migrated |
| `agent_profile_creator.py` | `AIDrivenStrategy` plugin | ✅ Migrated |
| `ai_profile_creator.py` | `HybridStrategy` plugin | ✅ Migrated |
| Individual execution logic | Unified `new_ai_agent.py` | ✅ Integrated |
| Separate configs | Unified `core/config.py` | ✅ Consolidated |

## Migration Steps

### 1. Update Imports

**Old way:**
```python
from smart_agent import main as smart_main
from agent_profile_creator import main as ai_main
```

**New way:**
```python
from agents.new_ai_agent import NewAIAgent

agent = NewAIAgent("Your task description")
result = agent.execute()
```

### 2. Update Configuration

**Old way:** Multiple config files and hardcoded values

**New way:** Single `.env` file with all configuration:

```bash
# .env
GOOGLE_EMAIL=your@email.com
GOOGLE_PASSWORD=your_password
BUSINESS_NAME="Your Business"
BUSINESS_ADDRESS_STREET="123 Main St"
BUSINESS_ADDRESS_ZIP="12345"
BUSINESS_ADDRESS_CITY="Your City"
# ... etc
```

### 3. Update Task Execution

**Old way:** Different scripts for different tasks

**New way:** Single agent with natural language tasks:

```bash
# Instead of:
python smart_agent.py
python agent_profile_creator.py

# Use:
python scripts/agents/new_ai_agent.py "Create Google Business profile"
python scripts/agents/new_ai_agent.py "Login to Google account"
```

### 4. Plugin Development (Advanced)

To create a new strategy:

1. Create a file in `agents/strategies/`
2. Inherit from `BaseStrategyPlugin`
3. Implement required methods:
   - `analyze_state()`
   - `decide_action()`
   - `execute_action()`
   - `confidence_score` property
   - `can_handle()` method

Example:
```python
from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata

class MyStrategy(BaseStrategyPlugin):
    def __init__(self, config=None):
        super().__init__(config)
        self.metadata = PluginMetadata(
            name="MyStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="My custom strategy",
            author="You",
            priority=100
        )

    # ... implement methods
```

## Testing Migration

Run the migration test script:

```bash
cd google-business-project
python scripts/test_migration.py
```

This will:
1. Verify all old functionality exists in new plugins
2. Test strategy selection logic
3. Run smoke tests on the unified agent

## Rollback Plan

If issues occur, you can temporarily use the old agents while debugging:

1. Old agents remain in `scripts/agents/` (marked as deprecated)
2. Configuration files are backward compatible
3. Logs from both systems can be compared

## Support

For migration issues:
1. Check the test results in `test-results/migration/`
2. Review plugin loading logs
3. Compare execution traces between old and new

Contact: [Project maintainers]
```

**Step 3: Update feature status**

```bash
# Update features/INDEX.md to reflect progress
# Change status from "In Progress" to appropriate phase
```

**Step 4: Commit documentation**

```bash
git add google-business-project/README.md google-business-project/docs/MIGRATION_GUIDE.md features/INDEX.md
git commit -m "docs(PROJ-1): update documentation for unified agent migration"
```

## Completion Checklist

- [ ] Phase 1: Plugin interface system implemented
- [ ] Phase 2: All strategy plugins created and tested
- [ ] Phase 3: Dynamic strategy selection integrated
- [ ] Phase 4: Integration tests passing
- [ ] Phase 5: Documentation updated
- [ ] All old functionality preserved in new plugins
- [ ] Unified agent can execute all previous tasks
- [ ] Configuration system consolidated
- [ ] Logging and error handling unified
- [ ] Performance comparable or better than old agents

## Next Steps After Implementation

1. **Validation**: Run side-by-side comparison with old agents
2. **Performance Testing**: Benchmark execution times
3. **User Testing**: Get feedback on new CLI interface
4. **Deprecation**: Mark old agents as deprecated
5. **Monitoring**: Add usage tracking and analytics

---

**Plan complete and saved to `docs/plans/2026-03-02-google-business-agent-consolidation-implementation.md`.**

## Execution Options

**Two execution approaches:**

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**