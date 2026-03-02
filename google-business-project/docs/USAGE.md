# Google Business Agent Usage Guide

This guide covers how to use the unified Google Business Agent with its plugin architecture.

## Table of Contents

1. [Basic Usage](#basic-usage)
2. [Strategy Configuration](#strategy-configuration)
3. [Advanced Usage](#advanced-usage)
4. [Troubleshooting](#troubleshooting)

## Basic Usage

### Command Line

```bash
# Basic task
python scripts/agents/new_ai_agent.py "Create a Google Business Profile"

# With configuration file
python scripts/agents/new_ai_agent.py "Login to Google" --config config.json

# Verbose output
python scripts/agents/new_ai_agent.py "Create profile" -v
```

### Python API

```python
from agents.new_ai_agent import NewAIAgent

# Create agent with task description
agent = NewAIAgent("Create a Google Business Profile for My Company")

# Execute the task
result = agent.execute()

# Check results
if result['status'] == 'completed':
    print("Task completed successfully!")
    print(f"Iterations: {result['execution']['iterations']}")
    print(f"Success rate: {result['execution']['success_rate']:.1%}")
else:
    print(f"Task failed: {result.get('error', 'Unknown error')}")
```

### Configuration Options

```python
agent = NewAIAgent(
    "Create Google Business Profile",
    config={
        "max_iterations": 30,      # Maximum agent loop iterations
        "headless": True,          # Run browser in headless mode
        "humanize": True,          # Add human-like delays
        "timeout": 60000,          # Browser timeout in ms
    }
)
```

## Strategy Configuration

### Available Strategies

| Strategy | Priority | Confidence | Description |
|----------|----------|------------|-------------|
| HybridStrategy | 20 | 0.65 | Combines AI + Rule-based (recommended) |
| AIDrivenStrategy | 30 | 0.10-0.80 | Uses AI vision (requires API key) |
| RuleBasedStrategy | 50 | 0.70 | Pattern matching (no API needed) |

### Strategy Selection

The agent automatically selects the best strategy based on:

1. **Can Handle**: Strategy must return `True` for `can_handle(browser_state)`
2. **Priority**: Lower number = higher preference
3. **Confidence**: Higher confidence = preferred

```python
# Check which strategy would be selected
agent = NewAIAgent("Test task")
browser_state = {"url": "https://accounts.google.com", "text": "Email", "inputs": [], "buttons": []}

strategy = agent._select_strategy(browser_state)
print(f"Selected: {strategy.metadata.name}")
print(f"Confidence: {strategy.confidence_score}")
```

### Forcing a Specific Strategy

```python
from agents.new_ai_agent import NewAIAgent
from agents.strategies.rule_based import RuleBasedStrategy

agent = NewAIAgent("Task")
agent.current_strategy = RuleBasedStrategy()
```

### Configuring AI Providers

For AIDrivenStrategy to work, configure API keys in `.env`:

```bash
# Option 1: Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-api03-...
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Option 2: DeepSeek (OpenAI-compatible)
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat
```

## Advanced Usage

### Custom Business Data

```python
agent = NewAIAgent("Create Business Profile", config={
    "business_name": "My Company GmbH",
    "business_address": {
        "street": "Hauptstraße 1",
        "zip": "12345",
        "city": "Berlin"
    },
    "business_phone": "+49 30 123456",
    "business_website": "https://mycompany.de",
    "business_category": "Softwareentwicklung"
})
```

### Monitoring Execution

```python
agent = NewAIAgent("Task")

# Before execution
print(f"Loaded strategies: {len(agent.plugin_manager.get_plugins())}")

# Execute
result = agent.execute()

# After execution
print(f"Status: {result['status']}")
print(f"Iterations: {result['execution']['iterations']}")
print(f"Duration: {result['execution']['duration_seconds']}s")
print(f"Actions taken: {result['execution']['action_count']}")

# View action history
for action in result['action_history'][-5:]:
    print(f"  - {action['action']['type']}: {action['result']['success']}")
```

### Accessing Memory

```python
agent = NewAIAgent("Task")
result = agent.execute()

# Memory summary
memory = result.get('memory', {})
print(f"Total actions recorded: {memory.get('total_actions', 0)}")
print(f"Success rate: {memory.get('success_rate', 0):.1%}")

# Learning insights
learning = result.get('learning', {})
print(f"Patterns learned: {learning.get('patterns_learned', [])}")
```

### Browser State Inspection

```python
agent = NewAIAgent("Task")

# During execution, you can inspect browser state
# (This requires browser to be initialized)
if agent.browser and agent.browser.page:
    state = agent._get_browser_state()
    print(f"Current URL: {state['url']}")
    print(f"Inputs: {len(state['inputs'])}")
    print(f"Buttons: {len(state['buttons'])}")
```

### Running with Specific Task Goals

```python
# Login task
login_agent = NewAIAgent("Login to Google account with my credentials")

# Profile creation task
profile_agent = NewAIAgent("Create Google Business Profile for SE Handwerk")

# Update task
update_agent = NewAIAgent("Update business hours on Google Business Profile")
```

## Troubleshooting

### Strategy Not Loading

**Symptom:** "No strategies loaded" or "0 Strategie-Plugins geladen"

**Solution:**
1. Check strategy files exist in `scripts/agents/strategies/`
2. Verify files implement `BaseStrategyPlugin`
3. Check for import errors:

```python
from agents.strategies.rule_based import RuleBasedStrategy
strategy = RuleBasedStrategy()  # Should not raise
```

### AI Strategy Low Confidence

**Symptom:** AIDrivenStrategy has confidence < 0.2

**Solution:**
1. Add API key to `.env`:
   ```bash
   ANTHROPIC_API_KEY=sk-ant-your-key
   ```
2. Verify key is valid:
   ```python
   import anthropic
   client = anthropic.Anthropic(api_key="your-key")
   # Should not raise
   ```

### Browser Not Starting

**Symptom:** Browser initialization fails

**Solution:**
1. Install camoufox: `pip install camoufox`
2. Check system dependencies
3. Try non-headless mode for debugging:
   ```python
   agent = NewAIAgent("Task", config={"headless": False})
   ```

### Task Not Completing

**Symptom:** Agent runs max iterations without completing

**Solution:**
1. Check action history to see what's happening:
   ```python
   for a in result['action_history']:
       print(f"{a['action']['type']}: {a['result']}")
   ```
2. Verify business data is correct
3. Try with `headless=False` to see browser

### Import Errors

**Symptom:** `ModuleNotFoundError: No module named 'agents...'`

**Solution:**
1. Run from correct directory:
   ```bash
   cd google-business-project
   python scripts/agents/new_ai_agent.py "Task"
   ```
2. Or use as module:
   ```bash
   cd google-business-project/scripts
   python -m agents.new_ai_agent "Task"
   ```

## Testing Your Setup

Run the verification script:

```bash
python scripts/test_unified_agent.py
```

Expected output:
```
============================================================
🧪 Unified Agent Test Suite
============================================================
📋 Testing strategy loading...
   ✓ Loaded 3 strategies
...
============================================================
📊 Results: 7 passed, 0 failed
============================================================
```

## Best Practices

1. **Start with RuleBasedStrategy** for predictable flows
2. **Enable AI for complex scenarios** where rules might not cover all cases
3. **Use HybridStrategy** for best of both worlds
4. **Monitor action history** during development
5. **Set reasonable max_iterations** (default 50 is good for most cases)
6. **Use headless=False** when debugging
7. **Keep business data up-to-date** in `config/business-data.json`