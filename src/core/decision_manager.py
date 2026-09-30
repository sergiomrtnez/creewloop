"""
Decision Manager for Human-in-the-Loop synchronization between CrewAI and Textual.
Uses threading.Event to pause synchronous worker threads and resume when the user responds.
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DecisionRequest:
    """Represents a request for human intervention from an agent."""
    question: str
    options: List[str] = field(default_factory=list)
    agent_name: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    default: Optional[str] = None


class DecisionManager:
    """
    Coordinates blocking decisions between CrewAI agents in background threads
    and the asynchronous Textual UI running on the main event loop.
    """

    def __init__(self) -> None:
        self._event = threading.Event()
        self._lock = threading.Lock()
        self._current_request: Optional[DecisionRequest] = None
        self._response: Optional[str] = None
        self._ui_callback: Optional[Callable[[DecisionRequest], None]] = None
        self._is_active = False

    def register_ui_callback(self, callback: Callable[[DecisionRequest], None]) -> None:
        """Register the callback that Textual UI provides to display decision prompts."""
        with self._lock:
            self._ui_callback = callback
            logger.info("DecisionManager: UI callback registered successfully.")

    def unregister_ui_callback(self) -> None:
        """Unregister the UI callback."""
        with self._lock:
            self._ui_callback = None

    @property
    def is_waiting(self) -> bool:
        """Check if currently waiting for user decision."""
        return self._is_active and not self._event.is_set()

    @property
    def current_request(self) -> Optional[DecisionRequest]:
        """Return the current decision request, if any."""
        return self._current_request

    def ask(
        self,
        question: str,
        options: Optional[List[str]] = None,
        agent_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> str:
        """
        Called by AskHumanDecisionTool inside the CrewAI worker thread.
        This blocks the thread until resolve() is called from Textual UI.
        """
        clean_options = [opt.strip() for opt in (options or []) if opt and opt.strip()]

        with self._lock:
            self._event.clear()
            self._response = None
            self._current_request = DecisionRequest(
                question=question,
                options=clean_options,
                agent_name=agent_name,
                context=context or {},
            )
            self._is_active = True
            callback = self._ui_callback

        logger.info("DecisionManager.ask called: %s (Options: %s)", question, clean_options)

        if callback is not None:
            try:
                callback(self._current_request)
            except Exception as e:
                logger.error("Error executing UI callback: %s", e, exc_info=True)
        else:
            logger.warning("No UI callback registered in DecisionManager. Cannot notify UI!")

        # Block the calling worker thread until the user resolves the decision
        signaled = self._event.wait(timeout=timeout)

        with self._lock:
            self._is_active = False
            response = self._response
            self._current_request = None

            if not signaled:
                logger.warning("DecisionManager timed out waiting for human input.")
                return "No human response received (timed out). Please proceed with the best assumption."

            logger.info("DecisionManager received resolution: %s", response)
            return response if response is not None else "Accepted without modification."

    def resolve(self, answer: str) -> None:
        """
        Called by the Textual UI when the user clicks an option or submits input.
        Sets the response and unblocks the waiting agent thread.
        """
        with self._lock:
            if not self._is_active:
                logger.warning("DecisionManager.resolve called but no decision was pending.")
                return
            self._response = answer
            self._event.set()
            logger.info("DecisionManager unblocked with response: %s", answer)

    def cancel(self, reason: str = "User cancelled the decision") -> None:
        """Cancel the current pending decision."""
        with self._lock:
            if self._is_active:
                self._response = f"Cancelled by user: {reason}"
                self._event.set()


# Global singleton instance for easy cross-module sharing
decision_manager = DecisionManager()


def get_decision_manager() -> DecisionManager:
    """Return the global DecisionManager instance."""
    return decision_manager
