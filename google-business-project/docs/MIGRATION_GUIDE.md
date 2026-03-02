# Migration Guide: From Legacy Agents to Unified Plugin Architecture

This guide helps you migrate from the legacy agent implementations (`smart_agent.py`, `agent_profile_creator.py`, `ai_profile_creator.py`) to the new unified plugin architecture.

## Overview

| Legacy Agent | New Equivalent | Changes Required |
|--------------|----------------|------------------|
| `smart_agent.py` | `RuleBasedStrategy` | Minimal - same logic, plugin interface |
| `agent_profile_creator.py` | `AIDrivenStrategy` | Configure API keys |
| `ai_profile_creator.py` | `HybridStrategy` | Combines both approaches |

## Quick Start Migration

### Before (Legacy)

```python
# Old way - running smart_agent.py directly
cd scripts/agents
python smart_agent.py
```

### After (Unified)

```python
# New way - using NewAIAgent
from agents.new_ai_agent import NewAIAgent

agent = NewAIAgent("Create a Google Business Profile")
result = agent.execute()
```

## Detailed Migration

### 1. From smart_agent.py → RuleBasedStrategy

**What changed:**
- Standalone script → Plugin class
- Global functions → Class methods
- Added plugin metadata and confidence scoring

**Old code:**
```python
# smart_agent.py
def get_page_state(page):
    state = {'url': page.url, ...}
    return state

def decide_next_action(state):
    if 'accounts.google.com' in state['url']:
        # ... decision logic
    return {'action': 'fill_input', ...}

def execute_action(page, action):
    # ... execution logic
```

**New code:**
```python
# strategies/rule_based.py
class RuleBasedStrategy(BaseStrategyPlugin):
    def analyze_state(self, browser_state):
        return {'url': browser_state['url'], ...}

    def decide_action(self, task, current_state, history):
        if 'accounts.google.com' in current_state['url']:
            # ... decision logic
        return {'type': 'fill_input', ...}

    def execute_action(self, action, browser_page):
        # ... execution logic
```

**Migration steps:**
1. No configuration changes needed
2. RuleBasedStrategy uses same business data and credentials
3. Update imports if using as library

### 2. From agent_profile_creator.py → AIDrivenStrategy

**What changed:**
- Standalone script → Plugin class
- Multi-provider initialization → Cleaner provider management
- Added fallback behavior when no API keys available

**Old code:**
```python
# agent_profile_creator.py
import anthropic

def ask_ai_for_action(state, goal, api_key=None):
    if api_key:
        client = anthropic.Anthropic(api_key=api_key)
        # ... API call
```

**New code:**
```python
# strategies/ai_driven.py
class AIDrivenStrategy(BaseStrategyPlugin):
    def __init__(self):
        self._init_ai_providers()  # Auto-detects API keys

    def decide_action(self, task, current_state, history):
        for provider in self.ai_providers:
            action = self._ask_ai(provider, ...)
```

**Migration steps:**
1. Set `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY` in `.env`
2. AIDrivenStrategy auto-detects available providers
3. Falls back gracefully if no API keys configured

### 3. From ai_profile_creator.py → HybridStrategy

**What changed:**
- Simulated AI decisions → Real strategy combination
- Better weighted decision making
- Success/failure tracking for learning

**Old code:**
```python
# ai_profile_creator.py
def ask_ai_for_action(page_context, business_data, api_key=None, model='gpt-4o'):
    # Placeholder for AI integration
    actions = []
    # ... rule-based fallback
```

**New code:**
```python
# strategies/hybrid.py
class HybridStrategy(BaseStrategyPlugin):
    def __init__(self):
        # Loads both AI and Rule strategies
        self._load_strategies()

    def decide_action(self, task, current_state, history):
        # Get decisions from all strategies
        # Weight by strategy weight * confidence
        # Return best decision
```

**Migration steps:**
1. HybridStrategy automatically combines available strategies
2. Weights: AI=0.7, Rule=0.3 (configurable)
3. No manual configuration needed

## Configuration Migration

### Old Configuration

```bash
# .env (legacy)
GOOGLE_EMAIL=your@email.com
GOOGLE_PASSWORD=yourpassword
ANTHROPIC_API_KEY=sk-ant-...  # Only for agent_profile_creator.py
```

### New Configuration

```bash
# .env (unified)
GOOGLE_EMAIL=your@email.com
GOOGLE_PASSWORD=yourpassword

# AI Strategy (optional - enables AIDrivenStrategy)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Alternative AI provider
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# Agent behavior
AGENT_MAX_ITERATIONS=50
AGENT_HEADLESS=true
AGENT_HUMANIZE=true
```

## API Changes

### Running the Agent

**Old:**
```python
# Each agent was standalone
import subprocess
subprocess.run(['python', 'smart_agent.py'])
```

**New:**
```python
# Unified interface
from agents.new_ai_agent import NewAIAgent

agent = NewAIAgent("Task description", config={
    "max_iterations": 50,
    "headless": True
})
result = agent.execute()
```

### Checking Results

**Old:**
```python
# Checked screenshots and log files
# agent-step-01.png, agent-final.html
```

**New:**
```python
# Structured result dictionary
result = agent.execute()
print(result['status'])  # 'completed' | 'error' | 'max_iterations_reached'
print(result['execution']['iterations'])
print(result['execution']['success_rate'])
print(result['action_history'])  # List of actions
```

## Feature Comparison

| Feature | Legacy | Unified |
|---------|--------|---------|
| Strategy selection | Manual (choose agent) | Automatic (best match) |
| Multiple AI providers | Per-agent | Unified (try all) |
| Fallback behavior | None | Graceful degradation |
| Test coverage | Minimal | 57 tests |
| Plugin system | None | Full plugin architecture |
| Logging | Print statements | Structured logging |
| Error handling | Try/except | Structured error hierarchy |

## Deprecation Timeline

| Version | Status |
|---------|--------|
| v1.0 (Current) | Legacy agents still available but deprecated |
| v1.1 | Legacy agents moved to `scripts/agents/deprecated/` |
| v2.0 | Legacy agents removed |

## Getting Help

1. Check [USAGE.md](USAGE.md) for detailed usage examples
2. Run `python scripts/test_unified_agent.py` to verify setup
3. Review tests in `tests/agents/strategies/` for examples
4. Check logs in `google_business_agent.log`

## Common Migration Issues

### Issue: "No strategies loaded"

**Cause:** Plugin directories not found

**Solution:**
```python
# Verify paths
from agents.plugin_manager import PluginManager
manager = PluginManager()
print(manager.plugin_dirs)  # Should show absolute paths
```

### Issue: "AI strategy has low confidence"

**Cause:** No AI API keys configured

**Solution:** Add API key to `.env`:
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### Issue: "Different behavior than legacy agent"

**Cause:** Strategy selection picking different strategy

**Solution:** Force specific strategy:
```python
from agents.new_ai_agent import NewAIAgent
from agents.strategies.rule_based import RuleBasedStrategy

agent = NewAIAgent("Task")
agent.current_strategy = RuleBasedStrategy()
# Or modify priority in strategy metadata
```

## Rollback

If you need to rollback to legacy agents:

```bash
# Legacy agents are still in place
cd scripts/agents
python smart_agent.py  # Still works
```

Note: Legacy agents will be removed in v2.0.