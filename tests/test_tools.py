"""
Unit Tests for Custom Tools (src/tools/).
Tests AskHumanDecisionTool, DockerValidationTool, and GitOpsTool.
"""

from __future__ import annotations

import threading
import time
from unittest.mock import patch
import pytest

from src.core.decision_manager import get_decision_manager
from src.core.event_bus import get_event_bus
from src.tools.docker_placeholder import DockerRunInput, DockerValidationTool
from src.tools.git_placeholder import GitOpsTool, GitRepoInput
from src.tools.human_decision_tool import AskHumanDecisionTool, HumanDecisionInput


class TestAskHumanDecisionTool:
    def test_schema_validation(self):
        valid = HumanDecisionInput(question="Confirm choice?", options=["Yes", "No"])
        assert valid.question == "Confirm choice?"
        assert valid.options == ["Yes", "No"]

        # Default options is None
        single = HumanDecisionInput(question="Review?")
        assert single.options is None

    def test_run_success_flow(self):
        tool = AskHumanDecisionTool()
        manager = get_decision_manager()
        bus = get_event_bus()

        logs = []
        statuses = []
        bus.subscribe_logs(lambda ev: logs.append(ev))
        bus.subscribe_status(lambda ev: statuses.append(ev))

        result = {}

        def worker():
            res = tool._run(question="Which database?", options=["SQLite", "PostgreSQL"])
            result["output"] = res

        t = threading.Thread(target=worker)
        t.start()
        time.sleep(0.05)

        # Resolve via manager
        manager.resolve("PostgreSQL")
        t.join(timeout=1.0)

        assert not t.is_alive()
        assert "User decision received: PostgreSQL" in result["output"]
        assert any("Requesting human decision" in l.message for l in logs)
        assert any("User responded: PostgreSQL" in l.message for l in logs)
        assert any(s.status == "asking" for s in statuses)

    def test_run_error_resilience(self):
        tool = AskHumanDecisionTool()
        manager = get_decision_manager()

        with patch.object(manager, "ask", side_effect=RuntimeError("Bus lock failure")):
            output = tool._run(question="Should we deploy?")
            assert "Error gathering human decision: Bus lock failure" in output
            assert "Proceeding with default assumption" in output


class TestDockerValidationTool:
    def test_schema_validation(self):
        model = DockerRunInput(command="pytest")
        assert model.command == "pytest"
        assert model.image == "python:3.11-slim"
        assert model.working_dir == "/workspace"

    def test_run_simulation(self):
        tool = DockerValidationTool()
        bus = get_event_bus()
        logs = []
        bus.subscribe_logs(lambda ev: logs.append(ev))

        output = tool._run(command="pytest -v", image="python:3.12-alpine")
        assert "pytest -v" in output
        assert any("Docker execution simulated" in l.message for l in logs)

    def test_run_daemon_unreachable_fallback(self):
        tool = DockerValidationTool()
        with patch("docker.from_env", side_effect=Exception("Connection refused")):
            output = tool._run(command="npm test")
            assert "npm test" in output


class TestGitOpsTool:
    def test_schema_validation(self):
        model = GitRepoInput(repo_name="my-project")
        assert model.repo_name == "my-project"
        assert model.commit_message == "Initial commit by CreewLoop Software Factory"
        assert model.branch == "main"
        assert model.push_remote is False

    def test_run_simulation(self):
        tool = GitOpsTool()
        bus = get_event_bus()
        logs = []
        bus.subscribe_logs(lambda ev: logs.append(ev))

        output = tool._run(
            repo_name="sample-repo",
            commit_message="feat: initial commit",
            branch="develop",
            push_remote=True,
        )
        assert "sample-repo" in output
        assert "develop" in output
        assert any("Git operation initialized" in l.message for l in logs)
