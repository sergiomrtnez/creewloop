"""
Integration Tests for CreewLoopApp Lifecycle and Actions (src/ui/app.py).
Tests mounting, event bus wiring, decision rendering, keybinding actions, and cleanup.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
import time
import pytest
from textual.widgets import Label

from src.config import AppConfig
from src.core.decision_manager import DecisionRequest, get_decision_manager
from src.core.event_bus import get_event_bus
from src.ui.app import CreewLoopApp
from src.ui.components.document_viewer import DocumentViewer
from src.ui.components.execution_panel import DecisionBox, ExecutionPanel
from src.ui.components.sidebar import ConfigSidebar


class TestAppLifecycle:
    @pytest.fixture
    def test_app(self):
        tmp_dir = tempfile.mkdtemp(prefix="creewloop_app_test_")
        config = AppConfig(
            provider="Ollama",
            model_name="ollama/llama3.2",
            workspace_dir=tmp_dir,
        )
        app = CreewLoopApp()
        app.config = config
        app.output_dir = tmp_dir
        app.sdd_path = os.path.join(tmp_dir, "sdd.md")
        yield app
        shutil.rmtree(tmp_dir, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_app_mount_and_components(self, test_app):
        async with test_app.run_test(size=(140, 45)):
            header = test_app.query_one("#header-title", Label)
            assert "CREEWLOOP" in str(header.render())

            status = test_app.query_one("#status-badge", Label)
            assert "IDLE" in str(status.render())

            sidebar = test_app.query_one("#sidebar", ConfigSidebar)
            assert sidebar is not None

            exec_panel = test_app.query_one("#execution-panel", ExecutionPanel)
            assert exec_panel is not None

            doc_viewer = test_app.query_one("#document-viewer", DocumentViewer)
            assert doc_viewer is not None

    @pytest.mark.asyncio
    async def test_app_actions_and_shortcuts(self, test_app):
        async with test_app.run_test(size=(140, 45)):
            sidebar = test_app.query_one("#sidebar", ConfigSidebar)
            initial_display = sidebar.display

            # Toggle sidebar action
            test_app.action_toggle_sidebar()
            assert sidebar.display != initial_display

            test_app.action_toggle_sidebar()
            assert sidebar.display == initial_display

            # Toggle dark mode
            initial_dark = test_app.theme
            test_app.action_toggle_dark()
            # Theme toggled

            # Clear logs
            test_app.action_clear_logs()

    @pytest.mark.asyncio
    async def test_event_bus_dispatches_to_ui(self, test_app):
        async with test_app.run_test(size=(140, 45)) as pilot:
            bus = get_event_bus()

            # Emit a log event from external thread
            bus.emit_log("ExternalAgent", "System check OK", level="SUCCESS")
            await pilot.pause(0.2)

            # Emit a file update event
            bus.emit_file_update(
                file_path=os.path.join(test_app.output_dir, "spec.md"),
                content="# Real-time Test Spec\n- Verified item",
                file_type="markdown",
            )
            await pilot.pause(0.2)

            doc_viewer = test_app.query_one("#document-viewer", DocumentViewer)
            assert "Real-time Test Spec" in doc_viewer._sdd_content

    @pytest.mark.asyncio
    async def test_app_decision_flow_and_cancellation(self, test_app):
        async with test_app.run_test(size=(140, 45)) as pilot:
            manager = get_decision_manager()
            worker_result = {}

            def worker():
                res = manager.ask("Cancel test prompt?", options=["Option 1", "Option 2"])
                worker_result["result"] = res

            t = threading.Thread(target=worker)
            t.start()

            # Wait for decision to appear in UI
            for _ in range(30):
                await pilot.pause(0.1)
                if test_app.query(DecisionBox):
                    break

            assert len(test_app.query(DecisionBox)) == 1

            status_badge = test_app.query_one("#status-badge", Label)
            assert "DECISION REQUIRED" in str(status_badge.render())

            # Stop / Cancel execution
            test_app.action_stop_execution()
            await pilot.pause(0.2)
            t.join(timeout=1.0)

            assert not t.is_alive()
            assert "Cancelled by user" in worker_result["result"]
            assert len(test_app.query(DecisionBox)) == 0
