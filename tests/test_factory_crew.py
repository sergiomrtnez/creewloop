"""
Unit Tests for Factory Crew & SDD Workflow (src/agents/factory_crew.py).
Verifies CrewAI agent setup, task dependencies, tool associations, and directory initialization.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import pytest
from crewai import LLM, Process

from src.agents.factory_crew import create_factory_crew
from src.config import build_crewai_llm
from src.core.event_bus import get_event_bus
from src.tools.human_decision_tool import AskHumanDecisionTool


class TestFactoryCrew:
    @pytest.fixture
    def test_llm(self):
        return build_crewai_llm("Ollama", "ollama/llama3.2")

    @pytest.fixture
    def temp_workspace(self):
        tmp_dir = tempfile.mkdtemp(prefix="creewloop_test_ws_")
        yield tmp_dir
        shutil.rmtree(tmp_dir, ignore_errors=True)

    def test_create_factory_crew_agents_and_tasks(self, temp_workspace, test_llm):
        project_prompt = "Build a real-time markdown editor with auto-save."

        crew = create_factory_crew(
            llm=test_llm,
            project_prompt=project_prompt,
            output_dir=temp_workspace,
        )

        assert crew is not None
        assert crew.process == Process.sequential

        # Verify 6 agents
        assert len(crew.agents) == 6
        agent_roles = [a.role for a in crew.agents]
        assert "Senior Product Manager" in agent_roles
        assert "Principal Software Architect" in agent_roles
        assert "UI/UX & Data Specialist" in agent_roles
        assert "Senior Full-Stack Developer" in agent_roles
        assert "Quality Assurance Engineer" in agent_roles
        assert "DevOps & Release Engineer" in agent_roles

        # Verify tools assigned
        pm = next(a for a in crew.agents if a.role == "Senior Product Manager")
        has_decision_tool = any(isinstance(t, AskHumanDecisionTool) for t in pm.tools)
        assert has_decision_tool is True

        # Verify 6 tasks
        assert len(crew.tasks) == 6
        task_descriptions = [t.description for t in crew.tasks]
        assert any("Software Design Document" in desc for desc in task_descriptions)
        assert any("Architecture" in desc for desc in task_descriptions)
        assert any("user interaction flow" in desc for desc in task_descriptions)
        assert any("implementation code" in desc for desc in task_descriptions)
        assert any("unit tests" in desc for desc in task_descriptions)
        assert any("Dockerfile" in desc for desc in task_descriptions)

    def test_workspace_directory_auto_created(self, test_llm):
        tmp_root = tempfile.mkdtemp()
        target_dir = os.path.join(tmp_root, "nested", "custom_output")
        try:
            assert not os.path.exists(target_dir)
            create_factory_crew(
                llm=test_llm,
                project_prompt="Test task",
                output_dir=target_dir,
            )
            assert os.path.exists(target_dir)
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    def test_custom_and_default_callbacks(self, temp_workspace, test_llm):
        step_events = []
        task_events = []

        def custom_step_cb(step):
            step_events.append(step)

        def custom_task_cb(task):
            task_events.append(task)

        crew = create_factory_crew(
            llm=test_llm,
            project_prompt="Test project",
            output_dir=temp_workspace,
            step_callback=custom_step_cb,
            task_callback=custom_task_cb,
        )

        assert crew.step_callback is custom_step_cb
        assert crew.task_callback is custom_task_cb
