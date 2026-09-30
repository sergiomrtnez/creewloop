"""
Automated Test for Concurrency Core:
Tests the AskHumanDecisionTool and DecisionManager synchronization mechanism
using threading.Event and simulated worker threads.
"""

from __future__ import annotations

import sys
import os
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.core.decision_manager import DecisionManager, DecisionRequest
from src.tools.human_decision_tool import AskHumanDecisionTool


def test_decision_manager_synchronization():
    print("==================================================================")
    print("[TEST] DecisionManager & AskHumanDecisionTool Concurrency")
    print("==================================================================")

    manager = DecisionManager()
    callback_received = []

    def fake_ui_callback(request: DecisionRequest):
        print(f"  [UI Simulation] Received prompt: '{request.question}'")
        print(f"  [UI Simulation] Rendered options: {request.options}")
        callback_received.append(request)

    manager.register_ui_callback(fake_ui_callback)

    agent_result = {}
    thread_started = threading.Event()

    def simulated_agent_worker():
        thread_started.set()
        print("  [Worker Thread] Agent started task...")
        print("  [Worker Thread] Agent invoking DecisionManager.ask()...")
        t0 = time.time()
        # This MUST block until resolve() is called
        answer = manager.ask(
            question="Which backend framework should we use?",
            options=["FastAPI", "Django", "Flask"],
            agent_name="Architect Agent",
        )
        elapsed = time.time() - t0
        print(f"  [Worker Thread] Agent unblocked after {elapsed:.2f}s with answer: '{answer}'")
        agent_result["answer"] = answer
        agent_result["elapsed"] = elapsed

    worker = threading.Thread(target=simulated_agent_worker, daemon=True)
    worker.start()

    # Wait for worker to enter blocked state
    thread_started.wait()
    time.sleep(0.3)

    assert manager.is_waiting, "FAILED: Manager should be in waiting state"
    assert len(callback_received) == 1, "FAILED: UI callback should have been invoked"
    print("  [Main Thread] Confirmed: Agent worker thread is successfully PAUSED.")

    # Simulate user pondering for 0.8 seconds before clicking an option
    print("  [Main Thread] Simulating user thinking...")
    time.sleep(0.8)

    chosen_option = "FastAPI"
    print(f"  [Main Thread] User clicks option button: '{chosen_option}'")
    manager.resolve(chosen_option)

    # Wait for worker thread to complete
    worker.join(timeout=2.0)
    assert not worker.is_alive(), "FAILED: Worker thread should have completed"
    assert agent_result.get("answer") == chosen_option, f"FAILED: Expected '{chosen_option}', got {agent_result.get('answer')}"
    assert not manager.is_waiting, "FAILED: Manager should no longer be waiting"

    print("\n[PASS] DecisionManager correctly pauses worker thread and resumes upon UI resolve()!")
    print("==================================================================\n")


if __name__ == "__main__":
    test_decision_manager_synchronization()
