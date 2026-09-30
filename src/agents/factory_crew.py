"""
Factory Crew definition orchestrating the Specification-Driven Development (SDD) flow.
Agents: Product Manager, Software Architect, UI/UX & Data Modeler, Senior Dev, QA, DevOps.
"""

from __future__ import annotations

import os
from typing import Any, Callable, Dict, Optional
from crewai import Agent, Crew, Process, Task
from crewai_tools import DirectoryReadTool, FileReadTool, FileWriterTool

from src.core.event_bus import get_event_bus
from src.tools.docker_placeholder import DockerValidationTool
from src.tools.git_placeholder import GitOpsTool
from src.tools.human_decision_tool import AskHumanDecisionTool


def create_factory_crew(
    llm: Any,
    project_prompt: str,
    output_dir: str,
    step_callback: Optional[Callable] = None,
    task_callback: Optional[Callable] = None,
) -> Crew:
    """
    Creates and configures the Software Factory Crew with SDD workflow.
    """
    os.makedirs(output_dir, exist_ok=True)
    bus = get_event_bus()

    # Tools
    human_tool = AskHumanDecisionTool()
    file_writer = FileWriterTool()
    file_reader = FileReadTool()
    dir_reader = DirectoryReadTool(directory=output_dir)
    docker_tool = DockerValidationTool()
    git_tool = GitOpsTool()

    sdd_file_path = os.path.join(output_dir, "sdd.md")

    # 1. Product Manager Agent
    pm_agent = Agent(
        role="Senior Product Manager",
        goal="Define precise project scope, requirements, user stories, and acceptance criteria.",
        backstory=(
            "You are a battle-tested technical Product Manager. You translate high-level requirements into "
            "actionable specifications. You prioritize customer value and always clarify ambiguities "
            "with the human stakeholder using the AskHumanDecisionTool."
        ),
        tools=[human_tool, file_writer, file_reader],
        llm=llm,
        verbose=True,
    )

    # 2. Software Architect Agent
    architect_agent = Agent(
        role="Principal Software Architect",
        goal="Select optimal tech stack, system architecture, database models, and design patterns.",
        backstory=(
            "You have designed distributed systems and clean architectures for over 15 years. "
            "You create robust technical designs, API schemas, and directory structures. "
            "You consult the human stakeholder using AskHumanDecisionTool on critical technology trade-offs."
        ),
        tools=[human_tool, file_writer, file_reader],
        llm=llm,
        verbose=True,
    )

    # 3. UI/UX & Data Modeler Agent
    ux_data_agent = Agent(
        role="UI/UX & Data Specialist",
        goal="Design user interaction flows, data models, schema migrations, and interface wireframes.",
        backstory=(
            "You bridge design aesthetics with database rigor. You craft user interaction journeys "
            "and relational/document data models. You validate key layout or schema decisions with the human."
        ),
        tools=[human_tool, file_writer, file_reader],
        llm=llm,
        verbose=True,
    )

    # 4. Senior Developer Agent
    dev_agent = Agent(
        role="Senior Full-Stack Developer",
        goal="Implement clean, production-ready, well-documented code based strictly on the approved SDD.",
        backstory=(
            "You write idiomatic, tested, modular code. You follow SOLID principles and clean architecture. "
            "You write real source files into the project directory and seek human approval on implementation nuances."
        ),
        tools=[human_tool, file_writer, file_reader, dir_reader],
        llm=llm,
        verbose=True,
    )

    # 5. QA Engineer Agent
    qa_agent = Agent(
        role="Quality Assurance Engineer",
        goal="Validate code correctness, run tests, and perform static analysis and security checks.",
        backstory=(
            "You are an unrelenting QA specialist. You design test suites and verify edge cases. "
            "You use containerized validation to ensure zero regressions before release."
        ),
        tools=[human_tool, docker_tool, file_reader],
        llm=llm,
        verbose=True,
    )

    # 6. DevOps Engineer Agent
    devops_agent = Agent(
        role="DevOps & Release Engineer",
        goal="Package software, configure CI/CD, and prepare Git versioning and release tags.",
        backstory=(
            "You automate deployments, container definitions, and git workflows. "
            "You ensure seamless delivery from local workspace to version control."
        ),
        tools=[human_tool, git_tool, file_reader, file_writer],
        llm=llm,
        verbose=True,
    )

    # TASKS

    # Task 1: Scope & Requirements Specification (PM)
    task_scope = Task(
        description=(
            f"Analyze the following user project request: '{project_prompt}'.\n"
            f"1. Identify core goals, user personas, MVP features, and non-functional requirements.\n"
            f"2. Use AskHumanDecisionTool to ask the human stakeholder to choose or validate the primary MVP scope.\n"
            f"3. Write the initial section of the Software Design Document (SDD) into '{sdd_file_path}'.\n"
            "Include Title, Project Scope, Feature Breakdown, and Acceptance Criteria."
        ),
        expected_output="Detailed Project Scope section appended to the SDD markdown file.",
        agent=pm_agent,
    )

    # Task 2: Architecture & Tech Stack Selection (Architect)
    task_architecture = Task(
        description=(
            f"Review the SDD in '{sdd_file_path}'.\n"
            "1. Propose suitable technology stack and architectural patterns.\n"
            "2. MUST use AskHumanDecisionTool to present 2-3 stack options (e.g. backend frameworks or database) "
            "and wait for the human decision.\n"
            f"3. Incorporate the human's chosen stack into '{sdd_file_path}' under 'System Architecture & Tech Stack'.\n"
            "Include component diagram structure, data flow, and file layout."
        ),
        expected_output="Complete Architecture specification updated in the SDD document.",
        agent=architect_agent,
    )

    # Task 3: UI/UX & Data Modeling (UX/Data)
    task_ux_data = Task(
        description=(
            f"Read '{sdd_file_path}'.\n"
            "1. Define the user interaction flow, API endpoints, and database models.\n"
            "2. If there are trade-offs (e.g., authentication approach or UI layout), consult the human with AskHumanDecisionTool.\n"
            f"3. Append the 'Data Models & Interface Specifications' to '{sdd_file_path}'."
        ),
        expected_output="Data schemas, API endpoints, and user flows documented in the SDD.",
        agent=ux_data_agent,
    )

    # Task 4: Implementation (Senior Dev)
    task_implementation = Task(
        description=(
            f"Read the completed SDD in '{sdd_file_path}'.\n"
            f"1. Write clean, working, modular implementation code into files inside '{output_dir}'.\n"
            "2. If clarification is needed, ask the user with AskHumanDecisionTool.\n"
            "3. Ensure the project has an entry point (e.g., main.py or app.py) and clear comments."
        ),
        expected_output=f"Working source code files written to '{output_dir}'.",
        agent=dev_agent,
    )

    # Task 5: QA Testing & Validation (QA)
    task_qa = Task(
        description=(
            f"Inspect the code in '{output_dir}'.\n"
            "1. Write unit tests (e.g., test_main.py) verifying core functionality.\n"
            "2. Use DockerValidationTool to simulate containerized execution.\n"
            "3. If any critical bug or design issue is suspected, ask the human with AskHumanDecisionTool."
        ),
        expected_output="Test files generated and container test execution logged.",
        agent=qa_agent,
    )

    # Task 6: DevOps & Versioning (DevOps)
    task_devops = Task(
        description=(
            f"Inspect all generated artifacts in '{output_dir}'.\n"
            "1. Create a Dockerfile and a README.md explaining how to run the software.\n"
            "2. Use GitOpsTool to simulate git repository initialization and initial commit.\n"
            "3. Ask the human with AskHumanDecisionTool if they are satisfied with the final delivery."
        ),
        expected_output="Dockerfile, README.md, and Git commit completed.",
        agent=devops_agent,
    )

    # Default internal callbacks to stream events to Textual
    def default_step_callback(step_output):
        bus.emit_log("CrewAI", f"Step progress: {str(step_output)[:180]}...", level="DEBUG")

    def default_task_callback(task_output):
        bus.emit_log("CrewAI", f"Completed task by {task_output.agent if hasattr(task_output, 'agent') else 'Agent'}", level="SUCCESS")
        # Check if SDD file exists and push update
        if os.path.exists(sdd_file_path):
            try:
                with open(sdd_file_path, "r", encoding="utf-8") as f:
                    bus.emit_file_update(sdd_file_path, f.read(), file_type="markdown", title="Software Design Document")
            except Exception:
                pass

    crew = Crew(
        agents=[pm_agent, architect_agent, ux_data_agent, dev_agent, qa_agent, devops_agent],
        tasks=[task_scope, task_architecture, task_ux_data, task_implementation, task_qa, task_devops],
        process=Process.sequential,
        verbose=True,
        step_callback=step_callback or default_step_callback,
        task_callback=task_callback or default_task_callback,
    )

    return crew
