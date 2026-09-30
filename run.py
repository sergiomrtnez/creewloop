"""
Entry point for CreewLoop Interactive Software Factory.
Runs the Textual TUI with CrewAI integration.
"""

from __future__ import annotations

import sys
import os

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ui.app import CreewLoopApp


def main():
    app = CreewLoopApp()
    app.run()


if __name__ == "__main__":
    main()
