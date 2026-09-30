"""
End-to-end Interactive Test for Textual UI + DecisionManager:
Simulates user launching the demo, an agent requesting a decision,
the UI mounting the DecisionBox with interactive buttons,
the user clicking an option, and the worker resuming.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.ui.app import CreewLoopApp
from src.ui.components.execution_panel import DecisionBox
from textual.widgets import Button


async def test_full_interactive_ui_flow():
    print("==================================================================")
    print("[TEST] Full Interactive Textual UI & Decision Flow")
    print("==================================================================")

    app = CreewLoopApp()
    async with app.run_test(size=(140, 45)) as pilot:
        print("  1. Textual App mounted.")

        # Click the 'Test Decision Flow' button
        print("  2. Triggering 'Test Decision Flow'...")
        demo_btn = app.query_one("#btn-demo", Button)
        demo_btn.scroll_visible()
        await pilot.pause(0.1)
        await pilot.click(demo_btn)

        # Wait for the background worker to invoke the PM decision request
        print("  3. Waiting for agent to request decision in UI...")
        for _ in range(50):
            await pilot.pause(0.1)
            decision_boxes = app.query(DecisionBox)
            if decision_boxes:
                break

        decision_boxes = app.query(DecisionBox)
        assert len(decision_boxes) > 0, "FAILED: DecisionBox did not mount in UI"
        print("  4. Confirmed: Agent paused and DecisionBox mounted on screen!")

        # Verify buttons exist in the DecisionBox
        box = decision_boxes.first()
        option_buttons = box.query(".option-btn")
        assert len(option_buttons) > 0, "FAILED: No option buttons rendered"
        print(f"  5. Found {len(option_buttons)} option buttons in DecisionBox.")

        # Simulate user clicking the first option (e.g. 'CLI Application')
        first_btn = option_buttons.first()
        first_btn.scroll_visible()
        await pilot.pause(0.1)
        print(f"  6. Simulating human clicking button: '{first_btn.label}'...")
        await pilot.click(first_btn)

        # Allow worker to resume
        await pilot.pause(0.5)

        # Verify that DecisionBox was removed after user resolved it
        assert len(app.query(DecisionBox)) == 0, "FAILED: DecisionBox should be unmounted after resolution"
        print("  7. Confirmed: DecisionBox unmounted, worker unblocked and running!")

        # Stop worker cleanly before closing the test runner
        stop_btn = app.query_one("#btn-stop", Button)
        await pilot.click(stop_btn)
        await pilot.pause(0.2)

    print("\n[PASS] End-to-end Textual UI & DecisionManager flow verified successfully!")
    print("==================================================================\n")


if __name__ == "__main__":
    asyncio.run(test_full_interactive_ui_flow())
