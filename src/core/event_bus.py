"""
Event Bus for decoupling CrewAI background threads from Textual UI.
Provides thread-safe dispatching of logs, agent thoughts, file updates, and lifecycle events.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import threading

logger = logging.getLogger(__name__)


@dataclass
class LogEvent:
    sender: str
    message: str
    level: str = "INFO"
    timestamp: Optional[str] = None


@dataclass
class FileUpdateEvent:
    file_path: str
    content: str
    file_type: str = "markdown"  # "markdown", "python", "yaml", etc.
    title: str = ""


@dataclass
class AgentStatusEvent:
    agent_name: str
    status: str  # "thinking", "acting", "asking", "idle", "completed"
    task_description: str = ""


class EventBus:
    """Thread-safe event dispatcher for application-wide notifications."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._log_listeners: List[Callable[[LogEvent], None]] = []
        self._file_listeners: List[Callable[[FileUpdateEvent], None]] = []
        self._status_listeners: List[Callable[[AgentStatusEvent], None]] = []

    def subscribe_logs(self, callback: Callable[[LogEvent], None]) -> None:
        with self._lock:
            if callback not in self._log_listeners:
                self._log_listeners.append(callback)

    def subscribe_files(self, callback: Callable[[FileUpdateEvent], None]) -> None:
        with self._lock:
            if callback not in self._file_listeners:
                self._file_listeners.append(callback)

    def subscribe_status(self, callback: Callable[[AgentStatusEvent], None]) -> None:
        with self._lock:
            if callback not in self._status_listeners:
                self._status_listeners.append(callback)

    def emit_log(self, sender: str, message: str, level: str = "INFO") -> None:
        event = LogEvent(sender=sender, message=message, level=level)
        with self._lock:
            listeners = list(self._log_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error("Error in log listener: %s", e)

    def emit_file_update(self, file_path: str, content: str, file_type: str = "markdown", title: str = "") -> None:
        event = FileUpdateEvent(file_path=file_path, content=content, file_type=file_type, title=title or file_path)
        with self._lock:
            listeners = list(self._file_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error("Error in file update listener: %s", e)

    def emit_agent_status(self, agent_name: str, status: str, task_description: str = "") -> None:
        event = AgentStatusEvent(agent_name=agent_name, status=status, task_description=task_description)
        with self._lock:
            listeners = list(self._status_listeners)
        for listener in listeners:
            try:
                listener(event)
            except Exception as e:
                logger.error("Error in agent status listener: %s", e)


event_bus = EventBus()


def get_event_bus() -> EventBus:
    return event_bus
