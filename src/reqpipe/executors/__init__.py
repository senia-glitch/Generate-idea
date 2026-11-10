"""Исполнители — адаптеры к AI-агентам. LLM по умолчанию не выбраны."""

from reqpipe.core.config import RunConfig
from reqpipe.core.errors import ExecutorError
from reqpipe.executors.base import ExecutionResult, Executor, Task


def make_executor(name: str, config: RunConfig) -> Executor:
    if name == "claude-code":
        from reqpipe.executors.claude_code import ClaudeCodeExecutor
        return ClaudeCodeExecutor(config.executors.get("claude-code"))
    if name == "opencode":
        from reqpipe.executors.opencode import OpenCodeExecutor
        return OpenCodeExecutor(config.executors.get("opencode"))
    if name == "mock":
        from reqpipe.executors.mock import MockExecutor
        return MockExecutor(config.executors.get("mock"))
    raise ExecutorError(
        f"Исполнитель {name!r} не запускается автоматически. В режиме manual конвейер ведёт сам агент: "
        "`reqpipe next` → выполнить задачу → `reqpipe submit`."
    )


__all__ = ["ExecutionResult", "Executor", "Task", "make_executor"]
