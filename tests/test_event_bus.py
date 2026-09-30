"""
Unit Tests for EventBus (src/core/event_bus.py).
Verifies thread-safe publish-subscribe mechanisms and error-resilience.
"""

from __future__ import annotations

import threading
import time
import pytest

from src.core.event_bus import (
    AgentStatusEvent,
    EventBus,
    FileUpdateEvent,
    LogEvent,
    get_event_bus,
)


class TestEventBus:
    def test_singleton_get_event_bus(self):
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2
        assert isinstance(bus1, EventBus)

    def test_log_subscription_and_emission(self):
        bus = EventBus()
        received_logs = []

        def log_handler(event: LogEvent):
            received_logs.append(event)

        bus.subscribe_logs(log_handler)
        bus.emit_log(sender="TestAgent", message="Hello world", level="INFO")
        bus.emit_log(sender="DevAgent", message="Syntax error", level="ERROR")

        assert len(received_logs) == 2
        assert received_logs[0].sender == "TestAgent"
        assert received_logs[0].message == "Hello world"
        assert received_logs[0].level == "INFO"

        assert received_logs[1].sender == "DevAgent"
        assert received_logs[1].message == "Syntax error"
        assert received_logs[1].level == "ERROR"

    def test_file_update_emission(self):
        bus = EventBus()
        received_files = []

        def file_handler(event: FileUpdateEvent):
            received_files.append(event)

        bus.subscribe_files(file_handler)
        bus.emit_file_update(file_path="output/sdd.md", content="# Architecture", file_type="markdown", title="SDD")

        assert len(received_files) == 1
        assert received_files[0].file_path == "output/sdd.md"
        assert received_files[0].content == "# Architecture"
        assert received_files[0].title == "SDD"

    def test_file_update_empty_title_fallback(self):
        bus = EventBus()
        received_files = []

        bus.subscribe_files(lambda ev: received_files.append(ev))
        bus.emit_file_update(file_path="output/main.py", content="print('hi')", file_type="python", title="")

        assert len(received_files) == 1
        assert received_files[0].title == "output/main.py"

    def test_agent_status_emission(self):
        bus = EventBus()
        received_statuses = []

        def status_handler(event: AgentStatusEvent):
            received_statuses.append(event)

        bus.subscribe_status(status_handler)
        bus.emit_agent_status(agent_name="Architect", status="thinking", task_description="Designing DB")

        assert len(received_statuses) == 1
        assert received_statuses[0].agent_name == "Architect"
        assert received_statuses[0].status == "thinking"
        assert received_statuses[0].task_description == "Designing DB"

    def test_faulty_listener_does_not_break_other_listeners(self):
        bus = EventBus()
        good_received = []

        def broken_listener(event: LogEvent):
            raise RuntimeError("Catastrophic listener failure!")

        def healthy_listener(event: LogEvent):
            good_received.append(event)

        bus.subscribe_logs(broken_listener)
        bus.subscribe_logs(healthy_listener)

        # Emission must not crash despite broken listener
        bus.emit_log("Core", "Test message")

        assert len(good_received) == 1
        assert good_received[0].message == "Test message"

    def test_idempotent_subscription(self):
        bus = EventBus()
        calls = []

        def handler(event: LogEvent):
            calls.append(event)

        bus.subscribe_logs(handler)
        bus.subscribe_logs(handler)  # duplicate subscription

        bus.emit_log("Core", "Single notification")
        assert len(calls) == 1

    def test_concurrent_emissions_and_subscriptions(self):
        bus = EventBus()
        counter = {"count": 0}
        lock = threading.Lock()

        def handler(event: LogEvent):
            with lock:
                counter["count"] += 1

        bus.subscribe_logs(handler)

        def worker():
            for _ in range(50):
                bus.emit_log("WorkerThread", "Ping")
                time.sleep(0.001)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert counter["count"] == 250
