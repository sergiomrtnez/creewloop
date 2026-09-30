"""
AskHumanDecisionTool for CrewAI agents.
Allows agents to pause execution and request decisions, feedback, or choices from the user.
"""

from __future__ import annotations

import logging
from typing import List, Optional, Type
from pydantic import BaseModel, Field
from crewai.tools import BaseTool

from src.core.decision_manager import DecisionManager, get_decision_manager
from src.core.event_bus import get_event_bus

logger = logging.getLogger(__name__)


class HumanDecisionInput(BaseModel):
    """Schema for human decision requests."""
    question: str = Field(
        ...,
        description="The specific question, architectural dilemma, scope clarification, or approval request for the human."
    )
    options: Optional[List[str]] = Field(
        default=None,
        description="List of concrete choices/options for the user to pick from (e.g. ['PostgreSQL', 'SQLite', 'MongoDB'] or ['Approve', 'Request Changes'])."
    )


class AskHumanDecisionTool(BaseTool):
    """
    CrewAI Tool that enables agents to interact with the human operator via Textual UI.
    Execution halts until the human selects an option or writes a custom answer.
    """
    name: str = "AskHumanDecisionTool"
    description: str = (
        "Crucial tool for Human-in-the-Loop decisions. Use this tool whenever you need human input, "
        "validation, architectural choices, scope approval, or feedback on a milestone. "
        "Provide a clear, concise question and 2 to 4 recommended options if applicable."
    )
    args_schema: Type[BaseModel] = HumanDecisionInput

    def _run(self, question: str, options: Optional[List[str]] = None) -> str:
        manager = get_decision_manager()
        bus = get_event_bus()

        options_list = options or []
        bus.emit_log("AskHumanDecisionTool", f"Requesting human decision: {question}", level="WARNING")
        bus.emit_agent_status("Human Decision", "asking", task_description=question)

        try:
            answer = manager.ask(
                question=question,
                options=options_list,
                agent_name="Agent",
            )
            bus.emit_log("AskHumanDecisionTool", f"User responded: {answer}", level="SUCCESS")
            bus.emit_agent_status("Agent", "acting", task_description="Resuming after user decision")
            return f"User decision received: {answer}"
        except Exception as e:
            logger.error("Error waiting for human decision: %s", e, exc_info=True)
            bus.emit_log("AskHumanDecisionTool", f"Decision error: {e}", level="ERROR")
            return f"Error gathering human decision: {str(e)}. Proceeding with default assumption."
