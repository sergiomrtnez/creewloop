"""
Reactive Document and Code Viewer Component for Textual UI.
Displays the Software Design Document (SDD) and generated code files in real-time.
"""

from __future__ import annotations

import os
from typing import Dict, Optional
from textual.app import ComposeResult
from textual.containers import Container, Vertical, VerticalScroll
from textual.widgets import Label, Markdown, Static, TabbedContent, TabPane


class DocumentViewer(Vertical):
    """Right Panel for reactive visualization of SDD markdown and source code."""

    DEFAULT_CSS = """
    DocumentViewer {
        width: 1fr;
        height: 100%;
        background: $background;
        padding: 1;
    }
    .panel-header {
        text-style: bold;
        color: $accent;
        padding-bottom: 1;
        border-bottom: solid $surface;
    }
    .viewer-scroll {
        height: 1fr;
        background: $surface;
        padding: 1;
        border: solid $surface-lighten-1;
    }
    #sdd-markdown {
        height: auto;
    }
    #code-markdown {
        height: auto;
    }
    .status-note {
        color: $text-muted;
        text-style: italic;
        margin-bottom: 1;
    }
    """

    INITIAL_SDD_PLACEHOLDER = """# Software Design Document (SDD)

*No specification generated yet.*

When the **Product Manager** and **Architect** agents run, this document will update reactively in real time.
"""

    INITIAL_CODE_PLACEHOLDER = """# Generated Source Code

*No source files written yet.*

As the **Senior Developer** and **QA** agents generate code, source files will be displayed here.
"""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._sdd_content = self.INITIAL_SDD_PLACEHOLDER
        self._code_content = self.INITIAL_CODE_PLACEHOLDER
        self._current_file: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Label("📄 SPECIFICATION & CODE VIEWER", classes="panel-header")

        with TabbedContent(initial="tab-sdd"):
            with TabPane("📋 SDD Document", id="tab-sdd"):
                with VerticalScroll(classes="viewer-scroll"):
                    yield Markdown(self._sdd_content, id="sdd-markdown")

            with TabPane("💻 Generated Code", id="tab-code"):
                with VerticalScroll(classes="viewer-scroll"):
                    yield Markdown(self._code_content, id="code-markdown")

            with TabPane("📁 File Artifacts", id="tab-files"):
                with VerticalScroll(classes="viewer-scroll"):
                    yield Static("No files generated yet.", id="files-list-widget")

    def update_sdd(self, content: str) -> None:
        """Update the SDD Markdown view with new content."""
        self._sdd_content = content
        markdown_widget = self.query_one("#sdd-markdown", Markdown)
        markdown_widget.update(content)

    def update_code(self, filename: str, code_content: str, language: str = "python") -> None:
        """Update the code tab with highlighted code."""
        self._current_file = filename
        formatted = f"### File: `{filename}`\n\n```{language}\n{code_content}\n```"
        self._code_content = formatted
        code_widget = self.query_one("#code-markdown", Markdown)
        code_widget.update(formatted)

    def refresh_artifacts(self, output_dir: str) -> None:
        """List generated artifacts in the output directory."""
        if not os.path.exists(output_dir):
            return

        files = []
        for root, _, filenames in os.walk(output_dir):
            for f in filenames:
                rel = os.path.relpath(os.path.join(root, f), output_dir)
                size = os.path.getsize(os.path.join(root, f))
                files.append(f"• **{rel}** ({size} bytes)")

        files_widget = self.query_one("#files-list-widget", Static)
        if files:
            files_widget.update("\n".join(files))
        else:
            files_widget.update("No artifacts generated yet.")
