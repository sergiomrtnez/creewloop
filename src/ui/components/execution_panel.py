"""
Execution & Decision Panel for Textual UI.
Displays agent logs, reasoning, and dynamically renders interactive buttons
when AskHumanDecisionTool requests human intervention.
"""

from __future__ import annotations

import logging
from typing import List, Optional
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, RichLog, Static

from src.core.decision_manager import DecisionRequest, get_decision_manager

logger = logging.getLogger(__name__)


class DecisionBox(Container):
    """Interactive container rendering questions, option buttons, and custom response input."""

    DEFAULT_CSS = """
    DecisionBox {
        height: auto;
        min-height: 8;
        background: $boost;
        border: heavy $warning;
        padding: 1;
        margin: 1 0;
    }
    .decision-title {
        color: $warning;
        text-style: bold;
    }
    .decision-question {
        color: $text;
        text-style: bold;
        margin-bottom: 1;
    }
    .options-grid {
        height: auto;
        layout: horizontal;
        align-horizontal: left;
        margin-bottom: 1;
    }
    .option-btn {
        margin-right: 1;
        min-width: 14;
    }
    .custom-row {
        height: auto;
        layout: horizontal;
    }
    .custom-input {
        width: 1fr;
        margin-right: 1;
    }
    """

    class OptionSelected(Message):
        def __init__(self, answer: str) -> None:
            super().__init__()
            self.answer = answer

    def __init__(self, request: DecisionRequest, **kwargs) -> None:
        super().__init__(**kwargs)
        self.request = request

    def compose(self) -> ComposeResult:
        agent_label = f"🤖 {self.request.agent_name or 'Agent'} needs your decision:"
        yield Label(agent_label, classes="decision-title")
        yield Label(f"❓ {self.request.question}", classes="decision-question")

        # Render discrete options as clickable buttons
        if self.request.options:
            with Horizontal(classes="options-grid"):
                variants = ["success", "primary", "warning", "default"]
                for idx, opt in enumerate(self.request.options):
                    v = variants[idx % len(variants)]
                    yield Button(opt, variant=v, classes="option-btn", id=f"opt-btn-{idx}")

        # Render custom text input for arbitrary user feedback
        with Horizontal(classes="custom-row"):
            yield Input(placeholder="Or type a custom instruction / feedback...", id="input-custom", classes="custom-input")
            yield Button("Submit Custom", variant="default", id="btn-submit-custom")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        event.stop()
        button_id = event.button.id or ""

        if button_id.startswith("opt-btn-"):
            idx = int(button_id.split("-")[-1])
            selected_answer = self.request.options[idx]
            self.post_message(self.OptionSelected(selected_answer))
        elif button_id == "btn-submit-custom":
            custom_val = self.query_one("#input-custom", Input).value.strip()
            if not custom_val:
                custom_val = "Accepted with default specifications."
            self.post_message(self.OptionSelected(custom_val))

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        custom_val = event.value.strip()
        if not custom_val:
            custom_val = "Accepted with default specifications."
        self.post_message(self.OptionSelected(custom_val))


class ExecutionPanel(Vertical):
    """Left Panel displaying CrewAI logs and interactive human decisions."""

    DEFAULT_CSS = """
    ExecutionPanel {
        width: 1fr;
        height: 100%;
        border-right: solid $primary-background;
        padding: 1;
        background: $background;
    }
    .panel-header {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
        border-bottom: solid $surface;
    }
    #log-stream {
        height: 1fr;
        background: $surface;
        border: solid $surface-lighten-1;
        padding: 1;
    }
    #decision-mount {
        height: auto;
    }
    """

    class HumanDecisionMade(Message):
        def __init__(self, answer: str) -> None:
            super().__init__()
            self.answer = answer

    def compose(self) -> ComposeResult:
        yield Label("💬 AGENT EXECUTION & INTERACTION", classes="panel-header")
        yield RichLog(id="log-stream", highlight=True, markup=True, wrap=True)
        yield Container(id="decision-mount")

    def add_log(self, sender: str, message: str, level: str = "INFO") -> None:
        """Appends formatted message to the log stream."""
        log_widget = self.query_one("#log-stream", RichLog)

        color_map = {
            "INFO": "cyan",
            "WARNING": "yellow",
            "ERROR": "red",
            "SUCCESS": "green",
            "DEBUG": "dim white",
        }
        color = color_map.get(level.upper(), "white")
        badge = f"[{color} bold][{sender}][/]"
        formatted = f"{badge} {message}"
        log_widget.write(formatted)

    def display_decision_prompt(self, request: DecisionRequest) -> None:
        """Mounts the interactive DecisionBox when an agent asks a question."""
        self.add_log(
            "HUMAN_INTERVENTION",
            f"Decision requested by {request.agent_name or 'Agent'}: [bold yellow]{request.question}[/]",
            level="WARNING",
        )
        mount_point = self.query_one("#decision-mount", Container)
        mount_point.remove_children()
        decision_box = DecisionBox(request=request)
        mount_point.mount(decision_box)
        decision_box.scroll_visible()

    def on_decision_box_option_selected(self, event: DecisionBox.OptionSelected) -> None:
        """Handles user clicking an option in the DecisionBox."""
        answer = event.answer
        mount_point = self.query_one("#decision-mount", Container)
        mount_point.remove_children()

        self.add_log("USER_DECISION", f"Answer submitted: [bold green]{answer}[/]", level="SUCCESS")

        # Resolve via DecisionManager to release CrewAI worker thread
        get_decision_manager().resolve(answer)
        self.post_message(self.HumanDecisionMade(answer))

    def clear_decisions(self) -> None:
        """Remove any active decision box."""
        mount_point = self.query_one("#decision-mount", Container)
        mount_point.remove_children()

    def clear_logs(self) -> None:
        """Clear all messages from the log stream."""
        log_widget = self.query_one("#log-stream", RichLog)
        log_widget.clear()
