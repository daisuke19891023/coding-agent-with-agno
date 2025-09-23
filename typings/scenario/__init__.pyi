
from collections.abc import Sequence
from typing import Any, Protocol

class AgentInput(Protocol):
    thread_id: str

    def last_new_user_message_str(self) -> str: ...

type AgentReturnTypes = Any

class AgentAdapter:
    async def call(self, agent_input: AgentInput) -> AgentReturnTypes: ...

class UserSimulatorAgent:
    def __init__(self, *, system_prompt: str | None = ...) -> None: ...

class JudgeAgent:
    def __init__(self, *, criteria: Sequence[str]) -> None: ...

def configure(
    *,
    default_model: str | None = ...,
    cache_key: str | None = ...,
    max_turns: int | None = ...,
) -> None: ...

async def run(
    *,
    name: str,
    description: str,
    agents: Sequence[Any],
    max_turns: int | None = ...,
) -> Any: ...
