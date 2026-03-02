#!/usr/bin/env python3
"""
AI-Driven Strategy Plugin for Google Business Agent

Extracted from agent_profile_creator.py, this strategy uses AI providers
(Anthropic, DeepSeek/OpenAI) to analyze screenshots and decide actions.
"""

import base64
import json
import time
import logging
import re
from typing import Dict, Any, List, Optional

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata


class AIDrivenStrategy(BaseStrategyPlugin):
    """
    AI-driven strategy extracted from agent_profile_creator.py.

    Uses vision-capable AI models to analyze screenshots and decide actions.
    Supports multiple AI providers with fallback behavior.
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize the AI-driven strategy.

        Args:
            config_overrides: Optional configuration overrides
        """
        super().__init__(config_overrides)

        self.logger = logging.getLogger(__name__)
        self.metadata = PluginMetadata(
            name="AIDrivenStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="AI-driven strategy with screenshot analysis",
            author="Migration from agent_profile_creator.py",
            priority=30  # Higher priority than rule-based (more advanced)
        )

        # AI provider configuration
        self.ai_providers: List[Dict[str, Any]] = []
        self.current_provider: Optional[str] = None
        self.provider_errors: Dict[str, str] = {}

        # Load configuration
        self._load_config()
        self._init_ai_providers()

        self.logger.info(f"AIDrivenStrategy initialized with {len(self.ai_providers)} AI providers")

    def _load_config(self):
        """Load configuration values."""
        try:
            from core.config import config
            self.anthropic_api_key = getattr(config, 'anthropic_api_key', None)
            self.anthropic_model = getattr(config, 'anthropic_model', 'claude-3-5-sonnet-20241022')
            self.openai_api_key = getattr(config, 'openai_api_key', None) or getattr(config, 'deepseek_api_key', None)
            self.openai_base_url = getattr(config, 'openai_base_url', None) or getattr(config, 'deepseek_base_url', None)
            self.openai_model = getattr(config, 'openai_model', 'gpt-4') or getattr(config, 'deepseek_model', 'deepseek-chat')
        except Exception as e:
            self.logger.warning(f"Could not load full config: {e}")
            self.anthropic_api_key = self.config.get('anthropic_api_key')
            self.anthropic_model = self.config.get('anthropic_model', 'claude-3-5-sonnet-20241022')
            self.openai_api_key = self.config.get('openai_api_key')
            self.openai_base_url = self.config.get('openai_base_url')
            self.openai_model = self.config.get('openai_model', 'gpt-4')

    def _init_ai_providers(self):
        """Initialize AI providers from config."""
        # Try Anthropic
        try:
            import anthropic
            if self.anthropic_api_key:
                self.ai_providers.append({
                    'name': 'anthropic',
                    'module': anthropic,
                    'client': anthropic.Anthropic(api_key=self.anthropic_api_key),
                    'model': self.anthropic_model
                })
                self.logger.info("✅ Anthropic provider loaded")
        except ImportError:
            self.logger.debug("Anthropic not available")
        except Exception as e:
            self.logger.warning(f"Anthropic initialization failed: {e}")

        # Try OpenAI/DeepSeek
        try:
            import openai
            if self.openai_api_key:
                client_kwargs = {'api_key': self.openai_api_key}
                if self.openai_base_url:
                    client_kwargs['base_url'] = self.openai_base_url

                self.ai_providers.append({
                    'name': 'openai',
                    'module': openai,
                    'client': openai.OpenAI(**client_kwargs),
                    'model': self.openai_model
                })
                self.logger.info("✅ OpenAI/DeepSeek provider loaded")
        except ImportError:
            self.logger.debug("OpenAI not available")
        except Exception as e:
            self.logger.warning(f"OpenAI initialization failed: {e}")

        if not self.ai_providers:
            self.logger.warning("⚠️ No AI providers available - strategy will use fallback")

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze browser state with optional screenshot capture.

        Args:
            browser_state: Raw browser state, may include 'page' for screenshot

        Returns:
            Analyzed state with screenshot information
        """
        # Capture screenshot if page provided
        if 'screenshot_b64' not in browser_state and 'page' in browser_state:
            try:
                screenshot_bytes = browser_state['page'].screenshot(type='png')
                browser_state['screenshot_b64'] = base64.b64encode(screenshot_bytes).decode()
            except Exception as e:
                self.logger.warning(f"Failed to capture screenshot: {e}")

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
        """
        Use AI to decide next action based on screenshot and context.

        Args:
            task: Task description and parameters
            current_state: Analyzed browser state
            history: Previous actions and results

        Returns:
            Action dictionary with type, details, reasoning, confidence
        """
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
        """
        Ask AI provider for decision.

        Args:
            provider: AI provider configuration
            context: Decision context
            current_state: Current browser state

        Returns:
            Action dictionary or None if failed
        """
        # Build prompt
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
2. click(selector) - click an element with text
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

        messages = [{"role": "user", "content": prompt}]

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
                # For OpenAI, add image to content if available
                if context['has_screenshot'] and current_state.get('screenshot_b64'):
                    messages[0]["content"] = [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{current_state.get('screenshot_b64')}"
                            }
                        }
                    ]
                response = provider['client'].chat.completions.create(
                    model=provider['model'],
                    messages=messages,
                    max_tokens=1000
                )
                content = response.choices[0].message.content
            else:
                return None

            # Parse JSON response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                action_data = json.loads(json_match.group())
                return {
                    'type': action_data.get('action', 'wait'),
                    'details': action_data.get('details', {}),
                    'reasoning': action_data.get('reasoning', 'AI decision'),
                    'confidence': action_data.get('confidence', 0.8)
                }
            else:
                self.logger.warning(f"Could not parse JSON from AI response: {content[:200]}")
                return None

        except Exception as e:
            self.logger.error(f"AI call failed: {e}")
            raise

    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """
        Execute AI-decided action.

        Args:
            action: Action dictionary from decide_action
            browser_page: Playwright/Camoufox page object

        Returns:
            Result dictionary with success status
        """
        action_type = action.get('action') or action.get('type')
        details = action.get('details', {})

        try:
            if action_type == 'navigate':
                url = details.get('url')
                browser_page.goto(url)
                return {'success': True, 'message': f'Navigated to {url}'}

            elif action_type == 'click':
                selector = details.get('selector') or details.get('text')
                if selector:
                    try:
                        browser_page.click(f'button:has-text("{selector}"), [role="button"]:has-text("{selector}")')
                    except:
                        browser_page.click(selector)
                    return {'success': True, 'message': f'Clicked {selector}'}
                return {'success': False, 'error': 'No selector provided'}

            elif action_type == 'fill':
                selector = details.get('selector') or details.get('input_index', 0)
                value = details.get('value')
                if isinstance(selector, int):
                    inputs = browser_page.locator('input:visible, textarea:visible').all()
                    if selector < len(inputs):
                        inputs[selector].fill(value)
                        return {'success': True, 'message': f'Filled input {selector}'}
                else:
                    browser_page.fill(selector, value)
                    return {'success': True, 'message': f'Filled {selector}'}
                return {'success': False, 'error': 'Could not fill input'}

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
        """
        Confidence score based on AI provider availability and success rate.

        Returns:
            Confidence between 0.0 and 1.0
        """
        if not self.ai_providers:
            return 0.1

        base_score = 0.8

        # Adjust based on error rate
        error_count = len(self.provider_errors)
        if error_count > 0:
            base_score -= (error_count * 0.1)

        return max(0.1, min(1.0, base_score))

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """
        Check if this strategy can handle the current state.

        Args:
            browser_state: Current browser state

        Returns:
            True if AI providers are available
        """
        return len(self.ai_providers) > 0