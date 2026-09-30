"""
Main Textual Application for CreewLoop Interactive Software Factory.
Coordinates background worker threads running CrewAI and the async reactive UI.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.widgets import Footer, Header, Label, Static

from src.agents.factory_crew import create_factory_crew
from src.config import AppConfig, build_crewai_llm
from src.core.decision_manager import DecisionRequest, get_decision_manager
from src.core.event_bus import FileUpdateEvent, LogEvent, get_event_bus
from src.ui.components.document_viewer import DocumentViewer
from src.ui.components.execution_panel import ExecutionPanel
from src.ui.components.sidebar import ConfigSidebar

logger = logging.getLogger(__name__)


class CreewLoopApp(App):
    """Interactive Software Factory TUI Application."""

    TITLE = "CREEWLOOP :: INTERACTIVE SOFTWARE FACTORY"
    SUB_TITLE = "Specification-Driven Development with CrewAI & Textual"
    CSS_PATH = "styles.tcss"

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True, priority=True),
        Binding("ctrl+b", "toggle_sidebar", "Toggle Config", show=True),
        Binding("ctrl+r", "refresh_view", "Refresh Files", show=True),
    ]

    def __init__(self, config: Optional[AppConfig] = None) -> None:
        super().__init__()
        self.config = config or AppConfig.from_env()
        self.output_dir = os.path.abspath(self.config.workspace_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.sdd_path = os.path.join(self.output_dir, "sdd.md")
        self._is_running = False

    def compose(self) -> ComposeResult:
        with Container(id="header-bar"):
            yield Label("⚡ CREEWLOOP FACTORY", id="header-title")
            yield Label("SDD Orchestration Engine (PM • Architect • UX • Dev • QA • DevOps)", id="header-subtitle")
            yield Label("● IDLE", id="status-badge")

        with Horizontal(id="main-container"):
            yield ConfigSidebar(config=self.config, id="sidebar")
            yield ExecutionPanel(id="execution-panel")
            yield DocumentViewer(id="document-viewer")

        yield Footer()

    def _dispatch_to_app(self, fn: Callable, *args: Any, **kwargs: Any) -> None:
        """Invokes a callback safely regardless of whether called from a worker thread or the main event loop."""
        import threading
        if getattr(self, "_thread_id", None) == threading.get_ident():
            fn(*args, **kwargs)
        else:
            self.call_from_thread(fn, *args, **kwargs)

    def on_mount(self) -> None:
        """Register listeners and thread callbacks on mount."""
        decision_mgr = get_decision_manager()
        bus = get_event_bus()

        # Connect DecisionManager to Textual via _dispatch_to_app for thread safety
        decision_mgr.register_ui_callback(
            lambda req: self._dispatch_to_app(self._on_decision_requested, req)
        )

        # Connect EventBus to Textual UI
        bus.subscribe_logs(
            lambda log_evt: self._dispatch_to_app(self._on_log_event, log_evt)
        )
        bus.subscribe_files(
            lambda file_evt: self._dispatch_to_app(self._on_file_event, file_evt)
        )

        # Initial logs
        exec_panel = self.query_one("#execution-panel", ExecutionPanel)
        exec_panel.add_log("SYSTEM", "CreewLoop Software Factory initialized.", level="SUCCESS")
        exec_panel.add_log("SYSTEM", f"Workspace output set to: {self.output_dir}", level="INFO")
        exec_panel.add_log("HINT", "Configure LLM provider and click 'Launch Factory' or 'Test Decision Flow'.", level="DEBUG")

        # Load existing SDD if present
        if os.path.exists(self.sdd_path):
            try:
                with open(self.sdd_path, "r", encoding="utf-8") as f:
                    doc_viewer = self.query_one("#document-viewer", DocumentViewer)
                    doc_viewer.update_sdd(f.read())
            except Exception:
                pass

    # Thread-Safe UI Update Handlers
    def _on_decision_requested(self, request: DecisionRequest) -> None:
        """Invoked on the Textual main thread when an agent pauses and requests a decision."""
        status_badge = self.query_one("#status-badge", Label)
        status_badge.update("⚠️ DECISION REQUIRED")
        status_badge.styles.color = "#d29922"

        exec_panel = self.query_one("#execution-panel", ExecutionPanel)
        exec_panel.display_decision_prompt(request)

    def _on_log_event(self, event: LogEvent) -> None:
        exec_panel = self.query_one("#execution-panel", ExecutionPanel)
        exec_panel.add_log(event.sender, event.message, event.level)

    def _on_file_event(self, event: FileUpdateEvent) -> None:
        doc_viewer = self.query_one("#document-viewer", DocumentViewer)
        if event.file_type == "markdown" or event.file_path.endswith(".md"):
            doc_viewer.update_sdd(event.content)
        else:
            doc_viewer.update_code(os.path.basename(event.file_path), event.content)
        doc_viewer.refresh_artifacts(self.output_dir)

    # Actions and Message Handlers
    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one("#sidebar", ConfigSidebar)
        sidebar.display = not sidebar.display

    def action_refresh_view(self) -> None:
        doc_viewer = self.query_one("#document-viewer", DocumentViewer)
        doc_viewer.refresh_artifacts(self.output_dir)
        if os.path.exists(self.sdd_path):
            with open(self.sdd_path, "r", encoding="utf-8") as f:
                doc_viewer.update_sdd(f.read())

    def on_config_sidebar_start_factory(self, message: ConfigSidebar.StartFactory) -> None:
        """User launched the live CrewAI factory."""
        if self._is_running:
            self.notify("Factory is already executing!", severity="warning")
            return

        self._is_running = True
        self.update_status("⚙️ RUNNING CREW", color="#58a6ff")
        self.run_crew_worker(
            provider=message.provider,
            model=message.model,
            api_key=message.api_key,
            base_url=message.base_url,
            prompt=message.prompt,
        )

    def on_config_sidebar_run_demo(self, message: ConfigSidebar.RunDemo) -> None:
        """User launched the interactive simulated demo."""
        if self._is_running:
            self.notify("An execution is already in progress!", severity="warning")
            return

        self._is_running = True
        self.update_status("⚡ RUNNING DEMO", color="#a371f7")
        self.run_demo_worker(prompt=message.prompt)

    def action_stop_execution(self) -> None:
        """Stops the current execution and clears pending decisions."""
        self.on_config_sidebar_stop_factory()

    def action_clear_logs(self) -> None:
        """Clears all messages from the execution log stream."""
        exec_panel = self.query_one("#execution-panel", ExecutionPanel)
        exec_panel.clear_logs()

    def on_config_sidebar_stop_factory(self) -> None:
        """User requested stop."""
        get_decision_manager().cancel("User pressed stop")
        self._is_running = False
        self.update_status("⏹ STOPPED", color="#f85149")
        exec_panel = self.query_one("#execution-panel", ExecutionPanel)
        exec_panel.add_log("SYSTEM", "Execution interrupted by user.", level="WARNING")
        exec_panel.clear_decisions()

    def on_execution_panel_human_decision_made(self, message: ExecutionPanel.HumanDecisionMade) -> None:
        self.update_status("⚙️ CREW RESUMED", color="#58a6ff")

    def on_unmount(self) -> None:
        """Ensure all worker threads and pending decisions are released on exit."""
        self._is_running = False
        get_decision_manager().cancel("Application closing")
        get_decision_manager().unregister_ui_callback()

    def update_status(self, text: str, color: str = "#8b949e") -> None:
        if not self.is_running:
            return
        try:
            status_badge = self.query_one("#status-badge", Label)
            status_badge.update(text)
            status_badge.styles.color = color
        except Exception:
            pass

    # Background Workers running in secondary threads
    @work(thread=True, exclusive=True)
    def run_crew_worker(self, provider: str, model: str, api_key: str, base_url: str, prompt: str) -> None:
        """
        Executes CrewAI in a background thread to prevent blocking Textual's event loop.
        """
        bus = get_event_bus()
        bus.emit_log("FactoryWorker", f"Starting CrewAI with provider={provider}, model={model}...", level="INFO")
        bus.emit_log("FactoryWorker", f"Project requirement: '{prompt}'", level="INFO")

        try:
            llm = build_crewai_llm(
                provider=provider,
                model_name=model,
                api_key=api_key or None,
                base_url=base_url or None,
            )

            crew = create_factory_crew(
                llm=llm,
                project_prompt=prompt,
                output_dir=self.output_dir,
            )

            bus.emit_log("FactoryWorker", "Kickoff initiated. Agents are collaborating...", level="SUCCESS")
            result = crew.kickoff()
            bus.emit_log("FactoryWorker", f"Crew execution completed successfully!", level="SUCCESS")
            bus.emit_log("Result", str(result)[:300] + ("..." if len(str(result)) > 300 else ""), level="INFO")

            self.call_from_thread(self.update_status, "✅ COMPLETED", "#3fb950")
            self.call_from_thread(self.action_refresh_view)

        except Exception as e:
            logger.error("Crew execution error: %s", e, exc_info=True)
            bus.emit_log("FactoryWorker", f"Execution failed: {str(e)}", level="ERROR")
            self.call_from_thread(self.update_status, "❌ ERROR", "#f85149")

        finally:
            self._is_running = False

    @work(thread=True, exclusive=True)
    def run_demo_worker(self, prompt: str) -> None:
        """
        Runs an end-to-end interactive simulation of the SDD flow and AskHumanDecisionTool.
        Exercises the exact same DecisionManager and threading.Event flow without needing API keys.
        """
        bus = get_event_bus()
        decision_mgr = get_decision_manager()

        bus.emit_log("DEMO", "Starting Interactive SDD Flow Simulation...", level="INFO")
        time.sleep(1)

        # Step 1: Product Manager
        bus.emit_log("Product Manager", f"Analyzing requirements for: '{prompt}'", level="INFO")
        time.sleep(1.5)
        bus.emit_log("Product Manager", "Consulting human stakeholder on MVP scope...", level="WARNING")

        pm_choice = decision_mgr.ask(
            question="What is the primary target deployment for this application?",
            options=["CLI Application", "REST API (FastAPI)", "Desktop GUI", "Full-Stack Web"],
            agent_name="Product Manager",
        )
        bus.emit_log("Product Manager", f"Stakeholder decision received: '{pm_choice}'. Writing SDD Scope...", level="SUCCESS")

        sdd_content = f"""# Software Design Document (SDD): {prompt}

## 1. Project Overview & Scope
- **Target Platform**: {pm_choice}
- **Objective**: Deliver a robust, tested, and maintainable software system for: "{prompt}".
- **Target Audience**: Developers, End-Users, and DevOps teams.

### 1.1 Acceptance Criteria
- [x] Clear CLI / API interfaces defined.
- [x] Structured data persistence layer.
- [x] Unit test coverage above 85%.
- [x] Containerized packaging ready.
"""
        with open(self.sdd_path, "w", encoding="utf-8") as f:
            f.write(sdd_content)
        bus.emit_file_update(self.sdd_path, sdd_content, file_type="markdown", title="Software Design Document")

        if not self._is_running:
            return

        time.sleep(1)

        # Step 2: Principal Architect
        bus.emit_log("Principal Architect", "Evaluating tech stack and architectural design...", level="INFO")
        time.sleep(1)

        if not self._is_running:
            return

        arch_choice = decision_mgr.ask(
            question="Which database and ORM architecture should we adopt for persistence?",
            options=["SQLite with SQLAlchemy", "Pydantic + JSON Flat Files", "PostgreSQL + Asyncpg"],
            agent_name="Principal Architect",
        )
        bus.emit_log("Principal Architect", f"Architecture approved: '{arch_choice}'. Updating SDD...", level="SUCCESS")

        sdd_content += f"""
## 2. System Architecture & Tech Stack
- **Persistence Layer**: {arch_choice}
- **Architecture Pattern**: Clean Layered Architecture (Domain Models -> Services -> Interfaces).
- **Core Dependencies**: Pydantic v2, Typer / FastAPI, Rich.

```
┌──────────────────────────────────────────────┐
│           Presentation Layer                 │
│         (CLI / REST Endpoints)               │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│             Business Logic                   │
│             (Domain Service)                 │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│            Persistence Layer                 │
│         ({arch_choice})                      │
└──────────────────────────────────────────────┘
```
"""
        with open(self.sdd_path, "w", encoding="utf-8") as f:
            f.write(sdd_content)
        bus.emit_file_update(self.sdd_path, sdd_content, file_type="markdown", title="Software Design Document")
        time.sleep(2)

        # Step 3: Senior Developer
        bus.emit_log("Senior Developer", "Generating production code files in workspace...", level="INFO")
        time.sleep(1.5)

        code_sample = '''"""
TaskManager Core Implementation
Auto-generated by CreewLoop Software Factory
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional


@dataclass
class Task:
    id: Optional[int]
    title: str
    description: str
    completed: bool = False
    created_at: str = datetime.utcnow().isoformat()


class TaskRepository:
    def __init__(self, db_path: str = "tasks.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    completed BOOLEAN DEFAULT 0,
                    created_at TEXT
                )
            """)

    def add_task(self, title: str, description: str = "") -> Task:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO tasks (title, description, completed, created_at) VALUES (?, ?, 0, ?)",
                (title, description, datetime.utcnow().isoformat())
            )
            task_id = cursor.lastrowid
            return Task(id=task_id, title=title, description=description)

    def list_tasks(self) -> List[Task]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title, description, completed, created_at FROM tasks")
            return [Task(*row) for row in cursor.fetchall()]


if __name__ == "__main__":
    repo = TaskRepository("sample_tasks.db")
    t = repo.add_task("Initial Task", "Created by CreewLoop Developer Agent")
    print(f"Created task: {t}")
    print(f"Total tasks: {len(repo.list_tasks())}")
'''
        app_file_path = os.path.join(self.output_dir, "task_manager.py")
        with open(app_file_path, "w", encoding="utf-8") as f:
            f.write(code_sample)

        bus.emit_file_update(app_file_path, code_sample, file_type="python", title="task_manager.py")
        bus.emit_log("Senior Developer", f"Successfully written '{app_file_path}'", level="SUCCESS")
        time.sleep(2)

        # Step 4: QA Engineer
        bus.emit_log("QA Engineer", "Running unit tests and container validation...", level="INFO")
        time.sleep(1.5)
        bus.emit_log("QA Engineer", "[DockerTool] Validated syntax and isolation test pass.", level="SUCCESS")

        # Step 5: DevOps
        bus.emit_log("DevOps Engineer", "Preparing Dockerfile and GitOps packaging...", level="INFO")
        dockerfile_content = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "task_manager.py"]
"""
        dockerfile_path = os.path.join(self.output_dir, "Dockerfile")
        with open(dockerfile_path, "w", encoding="utf-8") as f:
            f.write(dockerfile_content)

        bus.emit_file_update(dockerfile_path, dockerfile_content, file_type="dockerfile", title="Dockerfile")
        bus.emit_log("DevOps Engineer", "Git repository initialized and initial commit prepared.", level="SUCCESS")
        time.sleep(1)

        # Final Approval Decision
        final_choice = decision_mgr.ask(
            question="Software factory finished all steps. Approve the generated release artifacts?",
            options=["Approve & Package Release", "Request Modifications"],
            agent_name="DevOps Engineer",
        )
        bus.emit_log("DevOps Engineer", f"Final user response: '{final_choice}'.", level="SUCCESS")

        bus.emit_log("SYSTEM", "✨ All factory tasks successfully completed!", level="SUCCESS")
        self.call_from_thread(self.update_status, "✅ DEMO FINISHED", "#3fb950")
        self.call_from_thread(self.action_refresh_view)
        self._is_running = False
