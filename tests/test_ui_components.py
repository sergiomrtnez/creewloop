"""
Unit Tests for Textual UI Components (src/ui/components/).
Tests DecisionBox, ExecutionPanel, DocumentViewer, and ConfigSidebar widgets.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button, Input, Markdown, Select, Static, TextArea

from src.core.decision_manager import DecisionRequest
from src.ui.components.document_viewer import DocumentViewer
from src.ui.components.execution_panel import DecisionBox, ExecutionPanel
from src.ui.components.sidebar import ConfigSidebar


class TestUIComponents:
    @pytest.mark.asyncio
    async def test_decision_box_options_render_and_click(self):
        resolved_answers = []

        class DecisionTestApp(App):
            def compose(self) -> ComposeResult:
                req = DecisionRequest(
                    question="Select primary database",
                    options=["PostgreSQL", "SQLite", "MongoDB"],
                )
                yield DecisionBox(req)

            def on_decision_box_option_selected(self, message: DecisionBox.OptionSelected):
                resolved_answers.append(message.answer)

        app = DecisionTestApp()
        async with app.run_test() as pilot:
            box = app.query_one(DecisionBox)
            assert box is not None

            # Verify buttons
            buttons = app.query(".option-btn")
            assert len(buttons) == 3

            # Click second option: SQLite
            sqlite_btn = buttons[1]
            assert str(sqlite_btn.label) == "SQLite"
            await pilot.click(sqlite_btn)

            assert len(resolved_answers) == 1
            assert resolved_answers[0] == "SQLite"

    @pytest.mark.asyncio
    async def test_decision_box_custom_input_submit(self):
        resolved_answers = []

        class CustomInputTestApp(App):
            def compose(self) -> ComposeResult:
                req = DecisionRequest(
                    question="Provide custom requirements",
                    options=["Default"],
                )
                yield DecisionBox(req)

            def on_decision_box_option_selected(self, message: DecisionBox.OptionSelected):
                resolved_answers.append(message.answer)

        app = CustomInputTestApp()
        async with app.run_test() as pilot:
            input_widget = app.query_one("#input-custom", Input)
            input_widget.value = "Custom Redis Cache with TTL"

            submit_btn = app.query_one("#btn-submit-custom", Button)
            await pilot.click(submit_btn)

            assert len(resolved_answers) == 1
            assert resolved_answers[0] == "Custom Redis Cache with TTL"

    @pytest.mark.asyncio
    async def test_execution_panel_logs_and_decisions(self):
        class ExecPanelApp(App):
            def compose(self) -> ComposeResult:
                yield ExecutionPanel()

        app = ExecPanelApp()
        async with app.run_test() as pilot:
            panel = app.query_one(ExecutionPanel)

            # Test adding various log levels without errors
            panel.add_log("System", "Initializing", level="INFO")
            panel.add_log("Agent", "Low memory", level="WARNING")
            panel.add_log("Agent", "Exception caught", level="ERROR")
            panel.add_log("Agent", "Task complete", level="SUCCESS")
            panel.add_log("Worker", "Tick", level="DEBUG")

            # Mount decision prompt
            req = DecisionRequest(
                question="Approve Architecture?",
                options=["Approve", "Reject"],
                agent_name="Architect",
            )
            panel.display_decision_prompt(req)
            assert len(panel.query(DecisionBox)) == 1

            # Clear decisions
            panel.clear_decisions()
            await pilot.pause(0.1)
            assert len(panel.query(DecisionBox)) == 0

    @pytest.mark.asyncio
    async def test_config_sidebar_actions_and_provider_switching(self):
        dispatched_events = []

        class SidebarTestApp(App):
            def compose(self) -> ComposeResult:
                yield ConfigSidebar()

            def on_config_sidebar_start_factory(self, event: ConfigSidebar.StartFactory):
                dispatched_events.append(("START", event.provider, event.model))

            def on_config_sidebar_run_demo(self, event: ConfigSidebar.RunDemo):
                dispatched_events.append(("DEMO", event.prompt))

            def on_config_sidebar_stop_factory(self, event: ConfigSidebar.StopFactory):
                dispatched_events.append(("STOP",))

        app = SidebarTestApp()
        async with app.run_test(size=(140, 50)) as pilot:
            sidebar = app.query_one(ConfigSidebar)

            # Test provider selection change updates default model
            select = sidebar.query_one("#select-provider", Select)
            select.value = "OpenAI"
            await pilot.pause(0.1)

            model_input = sidebar.query_one("#input-model", Input)
            assert model_input.value == "openai/gpt-4o-mini"

            # Click Demo button
            demo_btn = sidebar.query_one("#btn-demo", Button)
            demo_btn.scroll_visible()
            await pilot.pause(0.1)
            await pilot.click(demo_btn)
            assert len(dispatched_events) == 1
            assert dispatched_events[0][0] == "DEMO"

            # Click Stop button
            stop_btn = sidebar.query_one("#btn-stop", Button)
            stop_btn.scroll_visible()
            await pilot.pause(0.1)
            await pilot.click(stop_btn)
            assert len(dispatched_events) == 2
            assert dispatched_events[1][0] == "STOP"

    @pytest.mark.asyncio
    async def test_document_viewer_reactive_updates(self):
        tmp_dir = tempfile.mkdtemp()
        try:
            # Create a mock file in tmp_dir
            sample_file = os.path.join(tmp_dir, "app.py")
            with open(sample_file, "w", encoding="utf-8") as f:
                f.write("print('Hello CreewLoop')")

            class DocViewerApp(App):
                def compose(self) -> ComposeResult:
                    yield DocumentViewer()

            app = DocViewerApp()
            async with app.run_test():
                viewer = app.query_one(DocumentViewer)

                # Update SDD
                viewer.update_sdd("# New Specification Title\n\n- Feature 1")
                assert "New Specification Title" in viewer._sdd_content

                # Update Code
                viewer.update_code("app.py", "print('hello')", language="python")
                assert "app.py" in viewer._code_content

                # Refresh artifacts
                viewer.refresh_artifacts(tmp_dir)
                files_widget = viewer.query_one("#files-list-widget", Static)
                assert "app.py" in str(files_widget.render())
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
