"""
Sidebar Component for LLM Provider configuration and project initialization.
"""

from __future__ import annotations

from typing import Optional
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Input, Label, Select, Static, TextArea

from src.config import PROVIDERS, AppConfig


class ConfigSidebar(VerticalScroll):
    """Configuration sidebar widget."""

    DEFAULT_CSS = """
    ConfigSidebar {
        width: 38;
        background: $surface;
        border-right: heavy $accent;
        padding: 1;
    }
    .section-title {
        color: $accent;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }
    .field-label {
        color: $text-muted;
        margin-top: 1;
    }
    .btn-action {
        margin-top: 1;
        width: 100%;
    }
    #txt-prompt {
        height: 6;
        margin-top: 1;
    }
    """

    class StartFactory(Message):
        """Dispatched when the user clicks 'Launch Factory'."""
        def __init__(self, provider: str, model: str, api_key: str, base_url: str, prompt: str) -> None:
            super().__init__()
            self.provider = provider
            self.model = model
            self.api_key = api_key
            self.base_url = base_url
            self.prompt = prompt

    class RunDemo(Message):
        """Dispatched when the user clicks 'Run Simulated Demo'."""
        def __init__(self, prompt: str) -> None:
            super().__init__()
            self.prompt = prompt

    class StopFactory(Message):
        """Dispatched when the user clicks 'Stop'."""
        pass

    def __init__(self, config: Optional[AppConfig] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.config = config or AppConfig.from_env()

    def compose(self) -> ComposeResult:
        yield Label("⚙️ FACTORY CONFIG", classes="section-title")

        yield Label("LLM Provider", classes="field-label")
        provider_options = [(p, p) for p in PROVIDERS.keys()]
        yield Select(
            provider_options,
            value=self.config.provider,
            id="select-provider",
            allow_blank=False,
        )

        yield Label("Model Name", classes="field-label")
        yield Input(
            value=self.config.model_name,
            placeholder="e.g. ollama/llama3.2 or openai/gpt-4o",
            id="input-model",
        )

        yield Label("API Key (if required)", classes="field-label")
        yield Input(
            value=self.config.api_key,
            placeholder="sk-...",
            password=True,
            id="input-api-key",
        )

        yield Label("Base URL / Endpoint", classes="field-label")
        yield Input(
            value=self.config.base_url,
            placeholder="http://localhost:11434",
            id="input-base-url",
        )

        yield Label("🎯 Project Specification", classes="section-title")
        yield TextArea(
            "Develop a lightweight CLI Task Manager with SQLite database and export to JSON.",
            id="txt-prompt",
        )

        yield Button("🚀 Launch Factory", variant="success", id="btn-start", classes="btn-action")
        yield Button("⚡ Test Decision Flow (Demo)", variant="primary", id="btn-demo", classes="btn-action")
        yield Button("⏹ Stop Execution", variant="error", id="btn-stop", classes="btn-action")

    def on_select_changed(self, event: Select.Changed) -> None:
        """Auto-fill default model and base URL when provider changes."""
        if event.select.id == "select-provider" and event.value in PROVIDERS:
            preset = PROVIDERS[str(event.value)]
            model_input = self.query_one("#input-model", Input)
            base_url_input = self.query_one("#input-base-url", Input)
            
            model_input.value = preset.default_model
            base_url_input.value = preset.default_base_url or ""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        button_id = event.button.id
        provider = str(self.query_one("#select-provider", Select).value)
        model = self.query_one("#input-model", Input).value.strip()
        api_key = self.query_one("#input-api-key", Input).value.strip()
        base_url = self.query_one("#input-base-url", Input).value.strip()
        prompt = self.query_one("#txt-prompt", TextArea).text.strip()

        if button_id == "btn-start":
            self.post_message(self.StartFactory(provider, model, api_key, base_url, prompt))
        elif button_id == "btn-demo":
            self.post_message(self.RunDemo(prompt))
        elif button_id == "btn-stop":
            self.post_message(self.StopFactory())
