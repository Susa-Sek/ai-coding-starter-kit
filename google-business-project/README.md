# Google Business Agent Project

Unified Google Business Profile automation agent with modular plugin architecture, supporting multiple strategies (rule-based, AI-driven, hybrid).

## Architecture Overview

The project uses a **plugin-based architecture** that allows different automation strategies to be swapped dynamically:

```
┌─────────────────────────────────────────────────────────────┐
│                      NewAIAgent                             │
│  (Main orchestrator - manages browser, state, execution)    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   PluginManager                             │
│  (Discovers and manages strategy plugins)                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│ RuleBased     │ │ AIDriven      │ │ Hybrid        │
│ Strategy      │ │ Strategy      │ │ Strategy      │
│ (priority:50) │ │ (priority:30) │ │ (priority:20) │
└───────────────┘ └───────────────┘ └───────────────┘
```

### Strategy Plugins

| Strategy | Priority | Description | Best For |
|----------|----------|-------------|----------|
| **HybridStrategy** | 20 | Combines AI + Rules with weighted decisions | General use, adaptive |
| **AIDrivenStrategy** | 30 | Uses Claude/DeepSeek for screenshot analysis | Complex scenarios, dynamic pages |
| **RuleBasedStrategy** | 50 | Pattern matching and heuristics | Predictable flows, fast execution |

## Project Structure

```
/google-business-project/
├── features/               # Feature specifications
├── scripts/
│   ├── core/               # Shared utilities
│   │   ├── config.py       # Configuration management
│   │   ├── logger.py       # Structured logging
│   │   ├── errors.py       # Error hierarchy
│   │   ├── plugin_base.py  # Plugin interface (NEW)
│   │   └── ...
│   ├── agents/
│   │   ├── new_ai_agent.py # Main unified agent (NEW)
│   │   ├── plugin_manager.py # Plugin lifecycle (NEW)
│   │   ├── strategies/     # Strategy plugins (NEW)
│   │   │   ├── rule_based.py
│   │   │   ├── ai_driven.py
│   │   │   └── hybrid.py
│   │   ├── smart_agent.py      # Legacy (deprecated)
│   │   ├── agent_profile_creator.py  # Legacy (deprecated)
│   │   └── ai_profile_creator.py     # Legacy (deprecated)
│   ├── browser/            # Browser automation
│   └── test_unified_agent.py  # Test script (NEW)
├── docs/
│   ├── USAGE.md            # Usage guide (NEW)
│   ├── MIGRATION_GUIDE.md  # Migration from legacy (NEW)
│   └── agent-functionality-inventory.md
├── tests/
│   ├── core/               # Core module tests
│   ├── agents/             # Agent tests
│   │   └── strategies/     # Strategy tests
│   ├── integration/        # Integration tests
│   ├── e2e/                # End-to-end tests
│   └── fixtures/           # Test fixtures
├── config/                 # Configuration files
└── README.md               # This file
```

## Quick Start

### 1. Setup

```bash
cd google-business-project

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure credentials
cp config/.env.example config/.env
cp config/business-data.json.example config/business-data.json
```

### 2. Run the Unified Agent

```bash
# Using Python module
python -m agents.new_ai_agent "Create a Google Business Profile"

# Or run the script directly
cd scripts
python agents/new_ai_agent.py "Create a Google Business Profile"
```

### 3. Run Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific test category
python -m pytest tests/e2e/test_smoke.py -v
python -m pytest tests/integration/ -v

# Run standalone test script
python scripts/test_unified_agent.py
```

## Configuration

### Environment Variables (.env)

| Variable | Description | Required |
|----------|-------------|----------|
| `GOOGLE_EMAIL` | Google account email | Yes |
| `GOOGLE_PASSWORD` | Google account password | Yes |
| `AGENT_MAX_ITERATIONS` | Max agent loop iterations | No (default: 50) |
| `AGENT_HEADLESS` | Run browser headless | No (default: true) |
| `AGENT_HUMANIZE` | Human-like behavior | No (default: true) |
| `ANTHROPIC_API_KEY` | Claude API key for AI strategy | No |
| `DEEPSEEK_API_KEY` | DeepSeek API key | No |

### Business Data (business-data.json)

```json
{
  "name": "Your Business Name",
  "address": {
    "street": "Street Address",
    "zip": "12345",
    "city": "City"
  },
  "phone": "+49 123 456789",
  "website": "https://example.com",
  "category": "Business Category"
}
```

## Strategy Selection

The agent automatically selects the best strategy based on:

1. **Can Handle Check**: Strategy must be able to handle current browser state
2. **Priority**: Lower priority number = higher preference
3. **Confidence Score**: Strategy's self-reported confidence (0.0-1.0)

### Example: Google Login Flow

```
Browser State: https://accounts.google.com
├── HybridStrategy.can_handle() → True (delegates to sub-strategies)
├── AIDrivenStrategy.can_handle() → False (no API key)
├── RuleBasedStrategy.can_handle() → True (Google URL detected)
└── Selected: RuleBasedStrategy (only one that can handle)
```

## Plugin Development

### Creating a New Strategy

```python
from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata

class MyCustomStrategy(BaseStrategyPlugin):
    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="MyCustomStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Custom strategy description",
            author="Your Name",
            priority=40  # Between AI (30) and Rule (50)
        )

    def analyze_state(self, browser_state):
        # Analyze and return structured state
        return {"analyzed": True, ...}

    def decide_action(self, task, current_state, history):
        # Decide next action
        return {"type": "click", "details": {...}, "confidence": 0.8}

    def execute_action(self, action, browser_page):
        # Execute the action
        return {"success": True, ...}

    @property
    def confidence_score(self):
        return 0.75

    def can_handle(self, browser_state):
        # Return True if this strategy can handle the state
        return "my-special-site.com" in browser_state.get("url", "")
```

### Registering a Plugin

Plugins in `scripts/agents/strategies/` are auto-discovered. Just create a new Python file and implement `BaseStrategyPlugin`.

## Migration from Legacy Agents

See [MIGRATION_GUIDE.md](docs/MIGRATION_GUIDE.md) for detailed migration instructions.

### Quick Migration

| Legacy Agent | Replacement |
|--------------|-------------|
| `smart_agent.py` | `RuleBasedStrategy` |
| `agent_profile_creator.py` | `AIDrivenStrategy` |
| `ai_profile_creator.py` | `HybridStrategy` |

## Testing

### Test Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Unit Tests | `tests/core/`, `tests/agents/` | Test individual components |
| Strategy Tests | `tests/agents/strategies/` | Test each strategy plugin |
| Integration Tests | `tests/integration/` | Test agent integration |
| E2E Tests | `tests/e2e/` | Smoke tests for full workflow |

### Running Tests

```bash
# All tests
pytest tests/ -v

# Specific category
pytest tests/agents/strategies/ -v
pytest tests/integration/ -v
pytest tests/e2e/test_smoke.py -v

# With coverage
pytest tests/ --cov=scripts --cov-report=html
```

## Security

- **No hardcoded credentials**: All loaded from environment
- **Configuration validation**: Required fields checked at startup
- **Secure logging**: Passwords masked in output
- **Structured errors**: Retryable vs non-retryable classification

## Troubleshooting

### Common Issues

1. **No strategies loaded**
   - Check `scripts/agents/strategies/` directory exists
   - Verify strategy files implement `BaseStrategyPlugin`

2. **AI strategy not working**
   - Set `ANTHROPIC_API_KEY` or `DEEPSEEK_API_KEY` in `.env`
   - Check API key is valid

3. **Browser fails to start**
   - Install camoufox: `pip install camoufox`
   - Check system dependencies

## License

Part of the AI Coding Starter Kit. See main project for license information.