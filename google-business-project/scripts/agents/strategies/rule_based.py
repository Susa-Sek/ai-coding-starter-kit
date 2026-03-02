#!/usr/bin/env python3
"""
Rule-Based Strategy Plugin for Google Business Agent

Extracted from smart_agent.py, this strategy uses pattern matching
and heuristics to decide actions based on URL and page content.
"""

import re
import time
import random
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata


@dataclass
class RuleBasedState:
    """Internal state tracking for rule-based strategy."""
    url: str
    text: str
    inputs: List[Dict[str, Any]]
    buttons: List[str]


class RuleBasedStrategy(BaseStrategyPlugin):
    """
    Rule-based strategy extracted from smart_agent.py.

    Uses URL patterns, text matching, and heuristics to decide actions.
    Good for predictable flows like Google login and business profile creation.
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize the rule-based strategy.

        Args:
            config_overrides: Optional configuration overrides
        """
        super().__init__(config_overrides)

        self.logger = logging.getLogger(__name__)
        self.metadata = PluginMetadata(
            name="RuleBasedStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Rule-based strategy with URL/text pattern matching",
            author="Migration from smart_agent.py",
            priority=50  # Medium priority
        )

        # Load credentials and business data from config
        self._load_config()

        # State tracking (from smart_agent.py)
        self.last_url = None
        self.consecutive_same_url = 0

        self.logger.info("RuleBasedStrategy initialized")

    def _load_config(self):
        """Load configuration values."""
        try:
            from core.config import config
            self.google_email = config.google_email
            self.google_password = config.google_password
            self.business_data = {
                'name': config.business_name,
                'street': config.business_address.get('street', '') if config.business_address else '',
                'zip': config.business_address.get('zip', '') if config.business_address else '',
                'city': config.business_address.get('city', '') if config.business_address else '',
                'phone': config.business_phone,
                'website': config.business_website,
                'category': config.business_category,
            }
        except Exception as e:
            self.logger.warning(f"Could not load full config: {e}")
            self.google_email = self.config.get('google_email', '')
            self.google_password = self.config.get('google_password', '')
            self.business_data = self.config.get('business_data', {})

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze browser state similar to smart_agent.py get_page_state.

        Args:
            browser_state: Raw browser state dictionary

        Returns:
            Analyzed state with additional computed fields
        """
        analyzed = {
            'url': browser_state.get('url', ''),
            'text': (browser_state.get('text', '') or '')[:3000],
            'inputs': browser_state.get('inputs', []),
            'buttons': browser_state.get('buttons', []),
            'title': browser_state.get('title', ''),
            'has_password_field': any(
                i.get('type') == 'password' for i in browser_state.get('inputs', [])
            ),
            'has_email_field': any(
                'email' in i.get('type', '').lower() for i in browser_state.get('inputs', [])
            ),
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
        """
        Decide next action based on rules from smart_agent.py decide_next_action.

        Args:
            task: Task description and parameters
            current_state: Analyzed browser state
            history: Previous actions and results

        Returns:
            Action dictionary with type, details, reasoning, confidence
        """
        url = current_state.get('url', '')
        text = current_state.get('text', '').lower()
        inputs = current_state.get('inputs', [])
        buttons = current_state.get('buttons', [])

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
            return self._handle_google_accounts(current_state)

        # Google Business Create flow
        if 'business.google.com' in url:
            return self._handle_google_business(current_state)

        # Default: Wait
        return {
            'type': 'wait',
            'details': {'seconds': 2},
            'reasoning': 'Warte auf Änderung',
            'confidence': 0.5
        }

    def _handle_google_accounts(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Accounts login flow."""
        url = current_state.get('url', '')
        text = current_state.get('text', '')
        inputs = current_state.get('inputs', [])

        # 2FA Challenge
        if 'challenge' in url:
            match = re.search(r'\b(\d{2})\b', current_state.get('text', ''))
            if match:
                return {
                    'type': 'wait_for_user',
                    'details': {
                        'message': f'NUMMER {match.group(1)} AUF PIXEL TIPPEN!',
                        'number': match.group(1)
                    },
                    'reasoning': f'2FA: Nummer {match.group(1)} auf Pixel tippen',
                    'confidence': 0.9
                }
            return {
                'type': 'wait_for_user',
                'details': {'message': 'Bitte bestätigen Sie auf Ihrem Pixel!'},
                'reasoning': '2FA - warte auf Benutzer',
                'confidence': 0.8
            }

        # Password page
        if ('challenge/pwd' in url or 'challenge/pw' in url or
            current_state.get('has_password_field', False)):
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
                    'details': {'value': self.google_password or ''},
                    'reasoning': 'Passwort eingeben',
                    'confidence': 0.9
                }

        # Email page
        text_lower = text.lower()
        if 'email' in text_lower or 'e-mail' in text_lower or current_state.get('has_email_field', False):
            email_input = next(
                (i for i in inputs if i.get('type') == 'email' or
                 'email' in i.get('aria_label', '').lower()),
                inputs[0] if inputs else None
            )

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
                    'details': {'index': 0, 'value': self.google_email or ''},
                    'reasoning': 'Email eingeben',
                    'confidence': 0.9
                }

        # Fallback: Look for continue button
        for btn in inputs.get('buttons', []) if isinstance(inputs, dict) else []:
            if 'weiter' in btn.lower() or 'next' in btn.lower():
                return {
                    'type': 'click_button',
                    'details': {'text': btn},
                    'reasoning': f'Klicke "{btn}"',
                    'confidence': 0.7
                }

        # Default wait
        return {
            'type': 'wait',
            'details': {'seconds': 2},
            'reasoning': 'Unbekannter Google Accounts Zustand',
            'confidence': 0.5
        }

    def _handle_google_business(self, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Google Business profile creation flow."""
        text = current_state.get('text', '').lower()
        inputs = current_state.get('inputs', [])
        buttons = current_state.get('buttons', [])

        # Look for active inputs
        active_inputs = [i for i in inputs if not i.get('disabled') and not i.get('readonly')]

        if active_inputs:
            first = active_inputs[0]
            idx = inputs.index(first) if first in inputs else 0

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
        """
        Execute action similar to smart_agent.py execute_action.

        Args:
            action: Action dictionary from decide_action
            browser_page: Playwright/Camoufox page object

        Returns:
            Result dictionary with success status
        """
        action_type = action.get('type')
        details = action.get('details', {})

        try:
            if action_type == 'fill_input':
                return self._execute_fill_input(details, browser_page)

            elif action_type == 'fill_password':
                return self._execute_fill_password(details, browser_page)

            elif action_type == 'click_button':
                return self._execute_click_button(details, browser_page)

            elif action_type == 'press_enter':
                return self._execute_press_enter(browser_page)

            elif action_type == 'wait':
                return self._execute_wait(details)

            elif action_type == 'wait_for_user':
                return self._execute_wait_for_user(details, browser_page)

            elif action_type == 'done':
                return {'success': True, 'message': 'Task completed', 'completed': True}

            else:
                return {'success': False, 'error': f'Unknown action type: {action_type}'}

        except Exception as e:
            self.logger.error(f"Action {action_type} failed: {e}")
            return {'success': False, 'error': str(e), 'message': f'Action {action_type} failed'}

    def _execute_fill_input(self, details: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute fill input action."""
        idx = details.get('index', 0)
        value = details.get('value', '')

        inputs = browser_page.locator('input:visible, textarea:visible').all()
        if idx < len(inputs):
            inputs[idx].click()
            time.sleep(random.uniform(0.3, 0.5))
            inputs[idx].fill(value)
            return {'success': True, 'message': f'Filled input {idx}'}

        return {'success': False, 'error': f'Input index {idx} not found'}

    def _execute_fill_password(self, details: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute fill password action."""
        value = details.get('value', '')

        pwd_input = browser_page.locator('input[type="password"]:visible').first
        pwd_input.click()
        time.sleep(random.uniform(0.3, 0.5))
        pwd_input.fill(value)
        return {'success': True, 'message': 'Filled password'}

    def _execute_click_button(self, details: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute click button action."""
        text = details.get('text', '')

        try:
            browser_page.click(f'button:has-text("{text}"), [role="button"]:has-text("{text}")')
            return {'success': True, 'message': f'Clicked button: {text}'}
        except Exception:
            # Fallback: Try pressing Enter
            try:
                browser_page.keyboard.press('Enter')
                return {'success': True, 'message': 'Pressed Enter as fallback'}
            except Exception as e:
                return {'success': False, 'error': str(e)}

    def _execute_press_enter(self, browser_page) -> Dict[str, Any]:
        """Execute press enter action."""
        browser_page.keyboard.press('Enter')
        return {'success': True, 'message': 'Pressed Enter'}

    def _execute_wait(self, details: Dict[str, Any]) -> Dict[str, Any]:
        """Execute wait action."""
        seconds = details.get('seconds', 2)
        time.sleep(seconds)
        return {'success': True, 'message': f'Waited {seconds}s'}

    def _execute_wait_for_user(self, details: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """Execute wait for user action (simplified)."""
        # In real implementation, this would poll for URL change
        return {'success': True, 'message': 'Waiting for user', 'requires_user': True}

    @property
    def confidence_score(self) -> float:
        """
        Confidence score based on rule coverage.

        Returns:
            Fixed confidence of 0.7 for rule-based strategies
        """
        return 0.7

    def can_handle(self, browser_state: Dict[str, Any]) -> bool:
        """
        Check if this strategy can handle the current state.

        Args:
            browser_state: Current browser state

        Returns:
            True if this is a Google-related page or German text detected
        """
        url = browser_state.get('url', '')
        text = (browser_state.get('text', '') or '').lower()

        # Can handle Google-related pages
        if 'google.com' in url:
            return True

        # Can handle pages with German text (smart_agent.py is German-focused)
        german_keywords = ['weiter', 'email', 'passwort', 'unternehmen', 'adresse', 'anmelden', 'erstellen']
        if any(word in text for word in german_keywords):
            return True

        return False