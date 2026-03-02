#!/usr/bin/env python3
"""
Hybrid Strategy Plugin for Google Business Agent

Combines rule-based and AI-driven strategies with weighted decision making.
Selects the best strategy based on confidence and state handling.
"""

import logging
import time
from typing import Dict, Any, List, Optional

from core.plugin_base import BaseStrategyPlugin, PluginType, PluginMetadata


class HybridStrategy(BaseStrategyPlugin):
    """
    Hybrid strategy that combines rule-based and AI approaches.

    Uses weighted scoring to select the best strategy for the current state.
    Tracks success/failure rates for adaptive learning.
    """

    def __init__(self, config_overrides: Optional[Dict[str, Any]] = None):
        """
        Initialize the hybrid strategy.

        Args:
            config_overrides: Optional configuration overrides
        """
        super().__init__(config_overrides)

        self.logger = logging.getLogger(__name__)
        self.metadata = PluginMetadata(
            name="HybridStrategy",
            version="1.0.0",
            plugin_type=PluginType.STRATEGY,
            description="Hybrid strategy combining rule-based and AI approaches",
            author="Migration",
            priority=20  # High priority (smart combination)
        )

        # Load sub-strategies
        self.strategies: List[Dict[str, Any]] = []
        self._load_strategies()

        # Track success/failure for learning
        self.success_counts: Dict[str, int] = {}
        self.failure_counts: Dict[str, int] = {}

        self.logger.info(f"HybridStrategy initialized with {len(self.strategies)} sub-strategies")

    def _load_strategies(self):
        """Dynamically load available strategies."""
        # Try to load AI-driven strategy
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
        except Exception as e:
            self.logger.warning(f"⚠️ AI-driven strategy initialization failed: {e}")

        # Try to load rule-based strategy
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
        except Exception as e:
            self.logger.warning(f"⚠️ Rule-based strategy initialization failed: {e}")

        if not self.strategies:
            self.logger.warning("⚠️ No sub-strategies available")

    def analyze_state(self, browser_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Let each strategy analyze the state.

        Args:
            browser_state: Raw browser state

        Returns:
            Combined analysis from all strategies
        """
        analyses = {}

        for strategy_info in self.strategies:
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
        """
        Use weighted combination of strategies to decide action.

        Args:
            task: Task description and parameters
            current_state: Analyzed browser state
            history: Previous actions and results

        Returns:
            Best action from available strategies
        """
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
                # Check if strategy can handle this state
                if not strategy_info['strategy'].can_handle(current_state):
                    self.logger.debug(f"Strategy {strategy_info['type']} cannot handle current state")
                    continue

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
            # All strategies failed or couldn't handle
            return {
                'type': 'wait',
                'details': {'seconds': 2},
                'reasoning': 'No strategy could handle current state - waiting',
                'confidence': 0.2
            }

        # Weight decisions by strategy weight and confidence
        weighted_decisions = []
        for d in decisions:
            weight = d['weight'] * d['confidence']
            weighted_decisions.append((weight, d))

        # Sort by weight (descending)
        weighted_decisions.sort(key=lambda x: x[0], reverse=True)

        # Use highest weighted decision
        best_weight, best = weighted_decisions[0]

        # Adjust confidence based on weight
        adjusted_confidence = min(0.95, best['decision'].get('confidence', 0.5) * (1 + best_weight))

        return {
            'type': best['decision'].get('type'),
            'details': best['decision'].get('details', {}),
            'reasoning': f"Hybrid: {best['decision'].get('reasoning', '')} (via {best['type']})",
            'confidence': adjusted_confidence
        }

    def execute_action(self, action: Dict[str, Any], browser_page) -> Dict[str, Any]:
        """
        Execute action and track success/failure for learning.

        Args:
            action: Action dictionary from decide_action
            browser_page: Playwright/Camoufox page object

        Returns:
            Result dictionary with success status
        """
        action_type = action.get('type')

        # Try to find which strategy would handle this action type best
        executing_strategy = None
        for strategy_info in self.strategies:
            if strategy_info['type'] == 'rule' and action_type in ['fill_input', 'click_button', 'wait_for_user', 'fill_password', 'press_enter']:
                executing_strategy = strategy_info['strategy']
                break
            elif strategy_info['type'] == 'ai' and action_type in ['navigate', 'click', 'fill', 'select', 'screenshot']:
                executing_strategy = strategy_info['strategy']
                break

        # Execute with best matching strategy or first available
        if not executing_strategy and self.strategies:
            executing_strategy = self.strategies[0]['strategy']

        if executing_strategy:
            try:
                result = executing_strategy.execute_action(action, browser_page)

                # Track success/failure
                strategy_type = next(
                    (s['type'] for s in self.strategies if s['strategy'] == executing_strategy),
                    'unknown'
                )
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
        """
        Confidence based on success rates of sub-strategies.

        Returns:
            Confidence between 0.0 and 1.0
        """
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
        """
        Check if any sub-strategy can handle the current state.

        Args:
            browser_state: Current browser state

        Returns:
            True if any sub-strategy can handle
        """
        return any(s['strategy'].can_handle(browser_state) for s in self.strategies)