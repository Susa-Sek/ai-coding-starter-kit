#!/usr/bin/env python3
"""
Neue KI-basierte Browser-Automation Lösung für Google Business Projekt.
Vollständig KI-getrieben, ohne hartcodierte Selektoren oder Flows.
"""

import time
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum

# Importiere Core-Module
from core.config import Config
from core.logger import setup_logger
from core.errors import GoogleBusinessAgentError

# Importiere neue Komponenten
from core.state_analyzer import StateAnalyzer, PageState, create_hybrid_analyzer
from agents.decision_engine import DecisionEngine, DecisionContext, DecisionResult, DecisionStrategy
from core.action_executor import ActionExecutor, ExecutionResult, create_executor
from core.memory_manager import MemoryManager, create_memory_manager
from agents.task_parser import TaskParser, ParsedTask, parse_task_description
from browser.enhanced_browser import EnhancedBrowser, BrowserConfig

# Plugin System
from agents.plugin_manager import PluginManager
from core.plugin_base import PluginType, BaseStrategyPlugin

logger = logging.getLogger(__name__)

class ActionType(Enum):
    """Typen von Aktionen, die der Agent ausführen kann."""
    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    WAIT = "wait"
    UPLOAD = "upload"
    EXECUTE_JS = "execute_js"
    TAKE_SCREENSHOT = "take_screenshot"
    DONE = "done"
    ERROR = "error"

@dataclass
class Action:
    """Repräsentiert eine Aktion, die ausgeführt werden soll."""
    type: ActionType
    details: Dict[str, Any]
    reasoning: str = ""
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Konvertiert Action zu Dictionary für JSON-Serialisierung."""
        return {
            "type": self.type.value,
            "details": self.details,
            "reasoning": self.reasoning,
            "confidence": self.confidence
        }

@dataclass
class BrowserState:
    """Repräsentiert den aktuellen Zustand des Browsers."""
    url: str
    title: str
    screenshot: Optional[str] = None  # Base64 encoded screenshot
    dom_summary: Optional[str] = None
    text_content: Optional[str] = None
    interactive_elements: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.interactive_elements is None:
            self.interactive_elements = []

@dataclass
class Task:
    """Repräsentiert eine Aufgabe für den Agenten."""
    description: str  # Natürlichsprachige Beschreibung
    goal: str  # Strukturiertes Ziel
    parameters: Dict[str, Any] = None
    constraints: List[str] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.constraints is None:
            self.constraints = []

class NewAIAgent:
    """
    Hauptklasse für den neuen KI-basierten Browser-Automation Agenten.
    """

    def __init__(self, task_description: str, config: Optional[Dict[str, Any]] = None):
        """
        Initialisiert den Agenten mit einer Aufgabenbeschreibung.

        Args:
            task_description: Natürlichsprachige Beschreibung der Aufgabe
            config: Konfigurationsparameter für den Agenten
        """
        self.logger = setup_logger("new_ai_agent")
        self.logger.info("🚀 Initialisiere neuen KI-Agenten")

        # Parse Aufgabe mit TaskParser
        self.task_parser = TaskParser()
        self.parsed_task = self.task_parser.parse(task_description, config)

        # Konvertiere zu internem Task-Format
        self.task = Task(
            description=self.parsed_task.raw_description,
            goal=self.parsed_task.goal,
            parameters=self.parsed_task.parameters,
            constraints=self.parsed_task.constraints
        )

        self.logger.info(f"📝 Aufgabe: {self.task.description}")
        self.logger.info(f"🎯 Ziel: {self.task.goal}")
        self.logger.info(f"📋 Parameter: {len(self.task.parameters)}")
        self.logger.info(f"⚖️ Constraints: {len(self.task.constraints)}")

        # Lade Konfiguration
        self.config = Config()

        # Agenten-Konfiguration
        self.agent_config = config or {}

        # Status Tracking
        self.current_state: Optional[PageState] = None
        self.action_history: List[Dict[str, Any]] = []
        self.iteration = 0
        self.max_iterations = self.agent_config.get("max_iterations", 50)
        self.task_id = None

        # Browser und Komponenten
        self.browser = None
        self.state_analyzer = None
        self.decision_engine = None
        self.action_executor = None
        self.memory_manager = None

        # Plugin System - initialize early for strategy access
        self.plugin_manager = PluginManager()
        try:
            self.plugin_manager.load_plugins()
            strategy_count = len(self.plugin_manager.get_plugins(PluginType.STRATEGY))
            self.logger.info(f"📦 {strategy_count} Strategie-Plugins geladen")
        except Exception as e:
            self.logger.warning(f"⚠️ Plugin-System Initialisierung fehlgeschlagen: {e}")

        self.current_strategy: Optional[BaseStrategyPlugin] = None

        self.logger.info("✅ Agent initialisiert")

    def execute(self) -> Dict[str, Any]:
        """
        Hauptausführungsmethode für den Agenten.

        Returns:
            Dictionary mit Ergebnissen und Status
        """
        self.logger.info("▶️ Starte Ausführung der Aufgabe")
        start_time = time.time()

        try:
            # Initialisiere Komponenten
            self._initialize_components()

            # Haupt-Ausführungsschleife
            while self.iteration < self.max_iterations:
                self.iteration += 1
                self.logger.info(f"🔄 Iteration {self.iteration}/{self.max_iterations}")

                # 1. Analysiere aktuellen Browser-Zustand
                self.current_state = self.state_analyzer.analyze(self.browser.page)

                # Zustand im Gedächtnis speichern
                state_summary = self.state_analyzer.summarize_state(self.current_state)

                # 2. Prüfe ob Aufgabe abgeschlossen ist
                if self._is_task_complete():
                    self.logger.info("🎉 Aufgabe erfolgreich abgeschlossen!")
                    break

                # 3. KI entscheidet nächste Aktion
                decision_context = self._create_decision_context()
                decision_result = self.decision_engine.decide_next_action(decision_context)

                # 4. Führe Aktion aus
                execution_result = self.action_executor.execute(
                    decision_result.action_type,
                    decision_result.action_details
                )

                # 5. Aktualisiere Gedächtnis
                self._update_memory(
                    state_before=state_summary,
                    action=decision_result.action_details,
                    result=asdict(execution_result),
                    state_after=self.state_analyzer.summarize_state(self.current_state)
                )

                # 6. Speichere in Historie
                self.action_history.append({
                    "iteration": self.iteration,
                    "decision": asdict(decision_result),
                    "execution": asdict(execution_result),
                    "state_before": state_summary
                })

                # 7. Prüfe auf Fehler und passe Strategie an
                if not execution_result.success:
                    self.logger.warning(f"⚠️ Aktion fehlgeschlagen: {execution_result.error}")
                    self.decision_engine.update_strategy_based_on_results([
                        DecisionResult(
                            action_type=decision_result.action_type,
                            action_details=decision_result.action_details,
                            reasoning=decision_result.reasoning,
                            confidence=decision_result.confidence,
                            strategy_used=decision_result.strategy_used
                        )
                    ])

                # 8. Warte für nächste Iteration
                time.sleep(1)

            # Bereite Ergebnis vor
            result = self._prepare_result(start_time)

            if self.iteration >= self.max_iterations:
                self.logger.warning("⚠️ Maximale Iterationen erreicht")
                result["status"] = "max_iterations_reached"

            # Speichere Gedächtnis
            self.memory_manager.save_memory()

            return result

        except Exception as e:
            self.logger.error(f"❌ Fehler während der Ausführung: {e}")
            return {
                "status": "error",
                "error": str(e),
                "iterations": self.iteration,
                "action_history": self.action_history
            }
        finally:
            # Browser schließen
            self._cleanup()

    def _initialize_components(self):
        """Initialisiert alle Komponenten des Agenten."""
        self.logger.info("🔧 Initialisiere Komponenten...")

        # 0. Plugin Manager (für Strategien)
        self.plugin_manager = PluginManager()
        try:
            self.plugin_manager.load_plugins()
            strategy_count = len(self.plugin_manager.get_plugins(PluginType.STRATEGY))
            self.logger.info(f"📦 {strategy_count} Strategie-Plugins geladen")
        except Exception as e:
            self.logger.warning(f"⚠️ Plugin-System nicht verfügbar: {e}")
            self.logger.info("ℹ️ Fallback auf integrierte DecisionEngine")

        # 1. Browser
        browser_config = BrowserConfig(
            headless=self.config.agent_headless,
            humanize=self.config.agent_humanize,
            locale=self.config.browser_locale,
            os=self.config.browser_os,
            geoip=self.config.browser_geoip,
            timeout=self.config.agent_timeout
        )

        self.browser = EnhancedBrowser(browser_config)
        self.browser.start()
        self.logger.info("✅ Browser initialisiert")

        # 2. State Analyzer
        self.state_analyzer = create_hybrid_analyzer(self.browser)
        self.logger.info("✅ State Analyzer initialisiert")

        # 3. Decision Engine
        self.decision_engine = DecisionEngine(strategy=DecisionStrategy.HYBRID)
        self.logger.info("✅ Decision Engine initialisiert")

        # 4. Action Executor
        self.action_executor = create_executor(self.browser)
        self.logger.info("✅ Action Executor initialisiert")

        # 5. Memory Manager
        self.memory_manager = create_memory_manager("memory/agent_memory")
        self.task_id = self.memory_manager.start_new_task(
            self.task.description,
            self.task.goal
        )
        self.logger.info("✅ Memory Manager initialisiert")

        self.logger.info("🔧 Alle Komponenten initialisiert")

    def _create_decision_context(self) -> DecisionContext:
        """Erstellt einen DecisionContext für die DecisionEngine."""
        return DecisionContext(
            task_description=self.task.description,
            task_goal=self.task.goal,
            task_parameters=self.task.parameters,
            current_state=self.current_state,
            action_history=self.action_history,
            iteration=self.iteration,
            max_iterations=self.max_iterations,
            strategy=DecisionStrategy.HYBRID
        )

    def _select_strategy(self, browser_state: Dict[str, Any]) -> Optional[BaseStrategyPlugin]:
        """
        Select the best strategy for current browser state.

        Args:
            browser_state: Current browser state dictionary

        Returns:
            Best matching strategy or None if no suitable strategy found
        """
        if not self.plugin_manager:
            self.logger.warning("⚠️ Plugin manager not initialized")
            return None

        try:
            strategy = self.plugin_manager.get_best_plugin(browser_state, PluginType.STRATEGY)
            if strategy:
                self.logger.info(f"🎯 Selected strategy: {strategy.metadata.name} "
                               f"(confidence: {strategy.confidence_score:.2f})")
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
        """
        Execute decision cycle with selected strategy.

        Args:
            strategy: Strategy plugin to use
            task: Task dictionary
            browser_state: Current browser state
            history: Action history

        Returns:
            Dictionary with action, result, strategy name, and confidence
        """
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

    def _get_browser_state(self) -> Dict[str, Any]:
        """
        Get current browser state for strategy analysis.

        Returns:
            Dictionary with url, title, text, inputs, buttons
        """
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

            # Try to get inputs and buttons
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
                    except Exception:
                        pass
            except Exception:
                state['inputs'] = []

            try:
                buttons = page.locator('button:visible, [role="button"]:visible').all()
                state['buttons'] = []
                for btn in buttons[:15]:
                    try:
                        text = btn.inner_text()[:50].strip()
                        if text:
                            state['buttons'].append(text)
                    except Exception:
                        pass
            except Exception:
                state['buttons'] = []

            return state

        except Exception as e:
            self.logger.error(f"❌ Browser state collection failed: {e}")
            return {'url': '', 'text': '', 'title': '', 'inputs': [], 'buttons': [], 'error': str(e)}

    def _update_memory(self, state_before: Dict[str, Any], action: Dict[str, Any],
                      result: Dict[str, Any], state_after: Dict[str, Any]):
        """Aktualisiert das Gedächtnis mit einer neuen Aktion."""
        learning_points = []

        if result.get("success"):
            learning_points.append(f"Erfolgreiche {action.get('type', 'unknown')} Aktion")
        else:
            learning_points.append(f"Fehler: {result.get('error', 'Unbekannt')}")

        self.memory_manager.record_action(
            state_before=state_before,
            action=action,
            result=result,
            state_after=state_after,
            learning_points=learning_points,
            tags=[self.task.goal, f"iteration_{self.iteration}"]
        )

    def _is_task_complete(self) -> bool:
        """
        Prüft ob die Aufgabe abgeschlossen ist.

        Heuristik basierend auf Ziel und aktuellem Zustand.
        """
        if not self.current_state:
            return False

        url = self.current_state.url.lower()
        title = self.current_state.title.lower()
        text = (self.current_state.text_content or "").lower()

        # Heuristik für Google Business Profile
        if self.task.goal == "create_google_business_profile":
            if "dashboard" in url or "locations" in url:
                return True
            if "profil erstellt" in text or "profil erfolgreich" in text:
                return True
            if "fertig" in text and "business" in text:
                return True

        # Heuristik für Login
        elif self.task.goal == "perform_login":
            if "welcome" in text or "willkommen" in text:
                return True
            if "dashboard" in url and "accounts.google.com" not in url:
                return True
            if "angemeldet als" in text or "signed in as" in text:
                return True

        # Allgemeine Heuristik
        if "success" in text or "erfolgreich" in text or "fertig" in text:
            if "error" not in text and "fehler" not in text:
                return True

        # Prüfe ob DONE-Aktion in Historie
        for entry in self.action_history:
            if entry.get("decision", {}).get("action_type") == "done":
                return True

        return False

    def _prepare_result(self, start_time: float) -> Dict[str, Any]:
        """
        Bereitet das Endergebnis vor.

        Args:
            start_time: Startzeit der Ausführung

        Returns:
            Dictionary mit Ergebnissen
        """
        duration = time.time() - start_time

        # Lerne aus dem Gedächtnis
        learning = self.memory_manager.learn_from_experience()
        memory_summary = self.memory_manager.get_memory_summary()

        result = {
            "status": "completed",
            "task": {
                "description": self.task.description,
                "goal": self.task.goal,
                "parameters": self.task.parameters
            },
            "execution": {
                "iterations": self.iteration,
                "duration_seconds": round(duration, 2),
                "action_count": len(self.action_history),
                "success_rate": learning.get("success_rate", 0)
            },
            "final_state": {
                "url": self.current_state.url if self.current_state else None,
                "title": self.current_state.title if self.current_state else None,
                "interactive_elements": len(self.current_state.interactive_elements) if self.current_state else 0
            },
            "learning": learning,
            "memory": memory_summary,
            "action_history": self.action_history[-10:]  # Letzte 10 Aktionen
        }

        return result

    def _cleanup(self):
        """Bereinigt Ressourcen."""
        self.logger.info("🧹 Bereinige Ressourcen...")

        if self.browser:
            try:
                self.browser.close()
                self.logger.info("✅ Browser geschlossen")
            except Exception as e:
                self.logger.warning(f"⚠️ Browser-Schließung fehlgeschlagen: {e}")

        if self.memory_manager and self.task_id:
            try:
                self.memory_manager.save_memory(self.task_id)
                self.logger.info("✅ Gedächtnis gespeichert")
            except Exception as e:
                self.logger.warning(f"⚠️ Gedächtnis-Speicherung fehlgeschlagen: {e}")

def main():
    """Hauptfunktion für Kommandozeilennutzung."""
    import argparse

    parser = argparse.ArgumentParser(description="Neuer KI-basierter Browser-Automation Agent")
    parser.add_argument("task", help="Aufgabenbeschreibung in natürlicher Sprache")
    parser.add_argument("--config", help="JSON Konfigurationsdatei")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose Ausgabe")

    args = parser.parse_args()

    # Lade Konfiguration falls angegeben
    config = {}
    if args.config:
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"❌ Fehler beim Laden der Konfiguration: {e}")
            return 1

    # Erstelle und starte Agenten
    print(f"🚀 Starte KI-Agenten mit Aufgabe: {args.task}")
    print(f"📋 Konfiguration: {len(config)} Parameter")

    try:
        agent = NewAIAgent(args.task, config)
        result = agent.execute()

        # Zeige Ergebnisse
        print(f"\n📊 Ergebnisse:")
        print(f"  Status: {result['status']}")
        print(f"  Iterationen: {result['execution']['iterations']}")
        print(f"  Dauer: {result['execution']['duration_seconds']}s")
        print(f"  Aktionen: {result['execution']['action_count']}")
        print(f"  Erfolgsrate: {result['execution']['success_rate']:.1%}")

        if result['final_state']['url']:
            print(f"  Finale URL: {result['final_state']['url'][:80]}...")

        if result['status'] == "completed":
            print("✅ Aufgabe erfolgreich abgeschlossen!")
        else:
            print("⚠️ Aufgabe nicht vollständig abgeschlossen")

        # Speichere detailliertes Ergebnis
        with open('agent_result.json', 'w') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print("💾 Detailliertes Ergebnis gespeichert: agent_result.json")

        return 0 if result['status'] == "completed" else 1

    except Exception as e:
        print(f"❌ Kritischer Fehler: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())