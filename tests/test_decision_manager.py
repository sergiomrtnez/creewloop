"""
Unit Tests for DecisionManager & Concurrency Core (src/core/decision_manager.py).
Tests all edge cases, timeouts, cancellations, and thread safety.
"""

from __future__ import annotations

import threading
import time
import pytest

from src.core.decision_manager import (
    DecisionManager,
    DecisionRequest,
    get_decision_manager,
)


class TestDecisionManager:
    def test_singleton_getter(self):
        m1 = get_decision_manager()
        m2 = get_decision_manager()
        assert m1 is m2
        assert isinstance(m1, DecisionManager)

    def test_options_cleaning_and_formatting(self):
        manager = DecisionManager()
        captured_req = []
        manager.register_ui_callback(lambda req: captured_req.append(req))

        def worker():
            manager.ask(
                question="Choose DB",
                options=["  PostgreSQL  ", "", "   ", "SQLite", None, "  MongoDB  "],
                timeout=0.2,
            )

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        assert len(captured_req) == 1
        assert captured_req[0].options == ["PostgreSQL", "SQLite", "MongoDB"]
        manager.resolve("PostgreSQL")
        t.join()

    def test_normal_ask_resolve_flow(self):
        manager = DecisionManager()
        received_request = []
        manager.register_ui_callback(lambda req: received_request.append(req))

        result = {}

        def worker():
            res = manager.ask("Which framework?", options=["FastAPI", "Flask"])
            result["response"] = res

        t = threading.Thread(target=worker)
        t.start()

        # Wait briefly for worker to enter wait
        time.sleep(0.05)
        assert manager.is_waiting is True
        assert manager.current_request is not None
        assert manager.current_request.question == "Which framework?"

        # Resolve
        manager.resolve("FastAPI")
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert result["response"] == "FastAPI"
        assert manager.is_waiting is False
        assert manager.current_request is None

    def test_timeout_returns_fallback_message(self):
        manager = DecisionManager()
        result = {}

        def worker():
            res = manager.ask("Deploy now?", timeout=0.1)
            result["response"] = res

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert "No human response received (timed out)" in result["response"]
        assert manager.is_waiting is False
        assert manager.current_request is None

    def test_cancel_decision_unblocks_worker(self):
        manager = DecisionManager()
        result = {}

        def worker():
            res = manager.ask("Confirm deletion?")
            result["response"] = res

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        assert manager.is_waiting is True
        manager.cancel(reason="Operation aborted by admin")
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert "Cancelled by user: Operation aborted by admin" in result["response"]
        assert manager.is_waiting is False

    def test_resolve_when_no_decision_pending_is_safe(self):
        manager = DecisionManager()
        # Should not raise exception
        manager.resolve("Premature answer")
        assert manager.is_waiting is False

    def test_cancel_when_no_decision_pending_is_safe(self):
        manager = DecisionManager()
        # Should not raise exception
        manager.cancel("No-op cancellation")
        assert manager.is_waiting is False

    def test_ui_callback_error_does_not_break_ask(self):
        manager = DecisionManager()

        def broken_callback(req):
            raise ValueError("UI rendering failed unexpectedly")

        manager.register_ui_callback(broken_callback)
        result = {}

        def worker():
            res = manager.ask("Critical question", timeout=0.1)
            result["response"] = res

        t = threading.Thread(target=worker)
        t.start()
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert "timed out" in result["response"]

    def test_unregister_ui_callback(self):
        manager = DecisionManager()
        called = []
        manager.register_ui_callback(lambda req: called.append(req))
        manager.unregister_ui_callback()

        def worker():
            manager.ask("Question with no UI", timeout=0.05)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert len(called) == 0

    def test_multiple_sequential_decisions(self):
        manager = DecisionManager()
        manager.register_ui_callback(lambda req: None)

        def worker(q, ans):
            return manager.ask(q, options=["A", "B"])

        answers = []
        for i in range(5):
            res_holder = {}

            def run_ask(idx):
                res_holder["ans"] = manager.ask(f"Question {idx}", timeout=1.0)

            t = threading.Thread(target=run_ask, args=(i,))
            t.start()
            time.sleep(0.02)
            manager.resolve(f"Answer {i}")
            t.join()
            answers.append(res_holder["ans"])

        assert answers == [f"Answer {i}" for i in range(5)]
