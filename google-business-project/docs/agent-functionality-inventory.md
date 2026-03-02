# Agent Functionality Inventory

> Analysis of existing Google Business agent implementations for consolidation into unified plugin architecture.
> Created: 2026-03-02

## Overview

This document inventories the functionality of three existing agent implementations:
1. `smart_agent.py` - Rule-based agent
2. `agent_profile_creator.py` - AI-driven agent with vision support
3. `ai_profile_creator.py` - Hybrid AI/rule-based agent

---

## 1. smart_agent.py Analysis

### 1.1 State Analysis Functions

| Function | Purpose | Key Features |
|----------|---------|--------------|
| `get_page_state(page)` | Collect browser state | URL, title, text, inputs, buttons |
| Global state tracking | URL change detection | `last_url`, `consecutive_same_url` |

**State Collection Details:**
- URL from `page.url`
- Title from `page.title()`
- Body text (limited to 3000 chars)
- Input fields (up to 10): type, placeholder, aria-label, name, disabled, readonly, value
- Buttons (up to 15): inner text

### 1.2 Decision Logic Patterns

| Pattern | Trigger | Action |
|---------|---------|--------|
| Stuck detection | `consecutive_same_url > 3` | Press Enter |
| Completion check | URL contains 'dashboard' or 'locations' | Done |
| Google Accounts - 2FA | URL contains 'challenge' | Wait for user |
| Google Accounts - Password | URL contains 'challenge/pwd' or password field | Fill password |
| Google Accounts - Email | Text contains 'email' or email input | Fill email |
| Business Create - Name | Text contains 'name'/'unternehmen' | Fill business name |
| Business Create - Category | Text contains 'kategorie'/'branche' | Fill category |
| Business Create - Address | Text contains 'adresse'/'straße' | Fill street |
| Button click | Button contains 'weiter'/'next'/'hinzufügen' | Click button |

### 1.3 Action Execution Functions

| Action | Implementation | Human Delay |
|--------|----------------|-------------|
| `fill_input` | Click input, fill value | 0.3-0.5s |
| `fill_password` | Click password field, fill | 0.3-0.5s |
| `click_button` | Click by text, fallback Enter | None |
| `press_enter` | Keyboard press Enter | None |
| `wait` | `time.sleep(seconds)` | N/A |
| `wait_for_user` | Poll for URL change (120s max) | N/A |
| `done` | Log completion, save HTML | N/A |

### 1.4 Configuration Usage

```python
GOOGLE_EMAIL = config.google_email
GOOGLE_PASSWORD = config.google_password
BUSINESS = {
    'name': config.business_name,
    'street': config.business_address.get('street', ''),
    'zip': config.business_address.get('zip', ''),
    'city': config.business_address.get('city', ''),
    'phone': config.business_phone,
    'website': config.business_website,
    'category': config.business_category,
}
```

### 1.5 Error Handling Patterns

- Try/except blocks around all browser interactions
- Fallback to Enter key if button click fails
- Silent failure with return `False` on errors
- Logging via `logger` from core module

---

## 2. agent_profile_creator.py Analysis

### 2.1 Screenshot-Based AI Analysis Flow

```
1. Capture screenshot → base64
2. Collect page state (URL, title, text, inputs, buttons)
3. Build prompt with state + goal
4. Send to AI API (Anthropic/DeepSeek)
5. Parse JSON response for action
6. Execute action
7. Repeat until done
```

### 2.2 Multi-AI Provider Support Structure

| Provider | Model Config | API Type |
|----------|--------------|----------|
| Anthropic | `config.anthropic_model` | Native SDK |
| DeepSeek | `config.deepseek_model` | OpenAI-compatible |
| Fallback | N/A | Local rules |

**Provider Selection:**
```python
ai_provider = config.ai_provider  # 'anthropic' or 'deepseek'
if ai_provider == 'anthropic' and HAS_ANTHROPIC and api_key:
    # Use Anthropic SDK
elif ai_provider == 'deepseek' and HAS_OPENAI and config.deepseek_api_key:
    # Use OpenAI-compatible API
else:
    # Fallback to decide_action_locally()
```

### 2.3 Base64 Image Encoding for API Calls

```python
# Anthropic format
{
    "type": "image",
    "source": {
        "type": "base64",
        "media_type": "image/png",
        "data": state['screenshot_b64'],
    },
}

# DeepSeek/OpenAI format
{
    "type": "image_url",
    "image_url": {
        "url": f"data:image/png;base64,{state['screenshot_b64']}"
    }
}
```

### 2.4 Goal-Oriented Task Execution

```python
GOAL = f"""
Erstelle ein Google Business Profil für {BUSINESS['name']} mit folgenden Daten:
- Name: {BUSINESS['name']}
- Adresse: {BUSINESS['street']}, {BUSINESS['zip']} {BUSINESS['city']}
- Telefon: {BUSINESS['phone']}
- Website: {BUSINESS['website']}
- Kategorie: {BUSINESS['category']}

Bei 2FA muss der Benutzer manuell bestätigen - warte dann auf Weiterleitung.
"""
```

### 2.5 AI Response Format

```json
{
    "thought": "What I see and what to do",
    "action": "fill" | "click" | "wait" | "wait_for_user" | "done" | "type",
    "details": {
        // Action-specific details
    }
}
```

---

## 3. ai_profile_creator.py Analysis

### 3.1 Hybrid Rule-Based/AI Approach

- Primary: AI decision (placeholder for Claude/GPT APIs)
- Fallback: Simulated AI with rule-based logic
- Uses same state collection as other agents

### 3.2 Fallback Strategy Patterns

```python
# When no AI API available, use intelligent rules
if 'accounts.google.com' in url:
    # Login flow handling
elif 'dashboard' in url or 'locations' in url:
    # Completion check
elif 'business.google.com' in url:
    # Business profile creation flow
```

### 3.3 Context-Aware Decision Making

- Analyzes page text for keywords
- Checks input field count and types
- Identifies button text for navigation
- Maintains iteration counter for loop protection

---

## 4. Feature Comparison Matrix

| Feature | smart_agent.py | agent_profile_creator.py | ai_profile_creator.py |
|---------|----------------|--------------------------|----------------------|
| **State Analysis** ||||
| URL collection | ✅ | ✅ | ✅ |
| Title collection | ✅ | ✅ | ✅ |
| Text extraction | ✅ (3000 chars) | ✅ (3000 chars) | ✅ (2000 chars) |
| Input detection | ✅ (10 limit) | ✅ (10 limit) | ✅ (10 limit) |
| Button detection | ✅ (15 limit) | ✅ (15 limit) | ✅ (10 limit) |
| Screenshot capture | ❌ | ✅ | ✅ |
| **Decision Logic** ||||
| Rule-based URL matching | ✅ | ✅ (fallback) | ✅ |
| Rule-based text matching | ✅ | ✅ (fallback) | ✅ |
| AI vision analysis | ❌ | ✅ | 🟡 (placeholder) |
| Multi-provider AI | ❌ | ✅ | 🟡 (placeholder) |
| 2FA handling | ✅ | ✅ | ✅ |
| Stuck detection | ✅ | ❌ | ❌ |
| **Actions** ||||
| fill_input | ✅ | ✅ | ✅ |
| fill_password | ✅ | ✅ (via fill) | ✅ (via fill) |
| click_button | ✅ | ✅ | ✅ |
| press_enter | ✅ | ✅ (via type) | ❌ |
| wait | ✅ | ✅ | ✅ |
| wait_for_user | ✅ | ✅ | ✅ |
| type text | ❌ | ✅ | ❌ |
| click_option | ❌ | ❌ | ✅ |
| done | ✅ | ✅ | ✅ |
| **Configuration** ||||
| Business data | ✅ | ✅ | ✅ |
| Headless mode | ✅ | ✅ | ✅ |
| Humanize | ✅ | ✅ | ✅ |
| Locale/OS/GeoIP | ✅ | ✅ | ✅ |
| Max iterations | ✅ | ✅ | ✅ |
| **Error Handling** ||||
| Try/except blocks | ✅ | ✅ | ✅ |
| Fallback actions | ✅ (Enter) | ✅ (local rules) | ✅ (rules) |
| Logging | ✅ | 🟡 (print) | 🟡 (print) |

---

## 5. Unique Features by Agent

### smart_agent.py Unique Features
1. **Stuck detection** - Detects when URL doesn't change and tries Enter
2. **Password-specific fill** - Separate action for password fields
3. **Full logging integration** - Uses core.logger module

### agent_profile_creator.py Unique Features
1. **Vision AI integration** - Screenshot analysis with Claude/DeepSeek
2. **Multi-provider support** - Anthropic and DeepSeek/OpenAI
3. **Goal-oriented prompting** - Structured goal passed to AI
4. **JSON response parsing** - Extracts action from AI response

### ai_profile_creator.py Unique Features
1. **Click option action** - Can click dropdown options by index
2. **Production code templates** - Commented code for Claude/OpenAI APIs
3. **Simpler architecture** - Easier to understand and modify

---

## 6. Recommended Plugin Architecture

Based on this analysis, the unified plugin architecture should:

### 6.1 Base Plugin Interface
```python
class BaseStrategyPlugin(ABC):
    def analyze_state(browser_state) -> Dict[str, Any]
    def decide_action(task, current_state, history) -> Dict[str, Any]
    def execute_action(action, browser_page) -> Dict[str, Any]
    def can_handle(browser_state) -> bool
    def confidence_score() -> float
```

### 6.2 Strategy Plugins

| Plugin | Priority | Confidence | When Active |
|--------|----------|------------|-------------|
| RuleBasedStrategy | 50 | 0.7 | Google URLs, German text |
| AIDrivenStrategy | 30 | 0.8-0.9 | When AI providers available |
| HybridStrategy | 20 | 0.8+ | Always (combines others) |

### 6.3 Shared Components

- **State Analyzer**: Collect browser state (URL, text, inputs, buttons, screenshot)
- **Action Executor**: Execute actions with human delay simulation
- **Memory Manager**: Track history and detect stuck states
- **Config Manager**: Load business data and credentials

---

## 7. Migration Notes

### 7.1 From smart_agent.py
- Extract `get_page_state()` → `StateAnalyzer.analyze()`
- Extract `decide_next_action()` → `RuleBasedStrategy.decide_action()`
- Extract `execute_action()` → `ActionExecutor.execute()`
- Extract stuck detection → `MemoryManager`

### 7.2 From agent_profile_creator.py
- Extract `ask_ai_for_action()` → `AIDrivenStrategy.decide_action()`
- Extract screenshot capture → `StateAnalyzer.capture_screenshot()`
- Extract multi-provider logic → `AIProviderRegistry`
- Extract fallback rules → Merge with `RuleBasedStrategy`

### 7.3 From ai_profile_creator.py
- Extract `get_page_context()` → Merge with `StateAnalyzer`
- Extract `execute_action()` → `ActionExecutor.execute()`
- Extract click_option → Add to `ActionExecutor`

---

## 8. Next Steps

1. Create `plugin_base.py` with `BaseStrategyPlugin` and `PluginRegistry`
2. Create `RuleBasedStrategy` from smart_agent.py logic
3. Create `AIDrivenStrategy` from agent_profile_creator.py logic
4. Create `HybridStrategy` combining both approaches
5. Integrate plugin system into `new_ai_agent.py`
6. Add comprehensive test coverage
7. Update documentation

---

*This inventory was created as part of PROJ-1: Google Business Agent Optimization*