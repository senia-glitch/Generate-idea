"""Mock-исполнитель: эталонные ответы элементов без LLM.

Нужен, чтобы прогнать весь конвейер офлайн (демо, тесты, проверка контрактов).
Фильтры из ``fail_once`` в первый раз «проваливаются» — так видна работа петель.
"""

from __future__ import annotations

import json

from reqpipe.core.config import ExecutorConfig
from reqpipe.core.errors import ExecutorError
from reqpipe.executors.base import ExecutionResult, Task


class MockExecutor:
    name = "mock"

    def __init__(self, config: ExecutorConfig | None):
        self.config = config or ExecutorConfig()

    def execute(self, task: Task) -> ExecutionResult:
        if task.kind == "arbiter":
            data = {"decision": "approve", "confidence": 0.85, "rationale": "mock: результат соответствует критерию"}
            return ExecutionResult(data=data, raw=json.dumps(data, ensure_ascii=False))
        ctx = task.context
        if ctx is None or ctx.element.example is None:
            raise ExecutorError(f"{task.element_id}: у элемента нет эталонного ответа для mock")
        element = ctx.element
        data = element.example(ctx)
        already_looped = any(ctx.loop_counts.get(f"{element.id}->{t}", 0) for t in element.loop_targets)
        if element.id in self.config.fail_once and element.loops and "verdict" in data and not already_looped:
            data = {**data, "verdict": "fail", "findings": [{
                "severity": "major", "target": element.default_loop_target(), "refs": [],
                "problem": "Демонстрационный возврат (mock): проверка работы петли доработки",
            }]}
        return ExecutionResult(data=data, raw=json.dumps(data, ensure_ascii=False))
