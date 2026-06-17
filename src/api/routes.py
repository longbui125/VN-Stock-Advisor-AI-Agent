from __future__ import annotations

from src.llm.llm_client import safe_invoke


def run_agent_turn(agent_executor, prompt: str, chat_history: list):
    return safe_invoke(
        agent_executor,
        {
            "input": prompt,
            "chat_history": chat_history,
        },
    )
