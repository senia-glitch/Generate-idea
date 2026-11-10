"""Общий интерфейс исполнителя и разбор JSON из ответа агента."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from reqpipe.core.element import Context


@dataclass
class Task:
    element_id: str
    title: str
    workspace: Path
    task_file: Path
    schema: dict[str, Any]
    schema_file: Path
    result_file: Path
    prompt: str
    capabilities: frozenset[str] = frozenset()
    model: str = ""
    extra_args: list[str] = field(default_factory=list)
    timeout_sec: int = 1800
    kind: str = "stage"               # stage | arbiter
    context: Context | None = None    # нужен mock-исполнителю
    log_file: Path | None = None


@dataclass
class ExecutionResult:
    data: dict[str, Any] | None
    raw: str = ""
    cost_usd: float = 0.0


class Executor(Protocol):
    name: str

    def execute(self, task: Task) -> ExecutionResult: ...


FENCE = re.compile(r"```(?:json)?\s*\n(.*?)```", re.DOTALL)


def extract_json(text: str) -> dict[str, Any] | None:
    """Достать JSON-объект из ответа агента: весь текст, блок ```json``` или первый сбалансированный {...}."""
    text = (text or "").strip()
    if not text:
        return None
    try:
        value = json.loads(text)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        pass
    for block in reversed(FENCE.findall(text)):
        try:
            value = json.loads(block)
            if isinstance(value, dict):
                return value
        except json.JSONDecodeError:
            continue
    start = text.find("{")
    while start != -1:
        depth, in_str, esc = 0, False, False
        for i in range(start, len(text)):
            ch = text[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
            elif ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        value = json.loads(text[start:i + 1])
                        if isinstance(value, dict):
                            return value
                    except json.JSONDecodeError:
                        break
                    break
        start = text.find("{", start + 1)
    return None


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """Развернуть $ref/$defs — некоторые агенты принимают только плоскую JSON-схему."""
    defs = schema.get("$defs", {})

    def resolve(node: Any, depth: int = 0) -> Any:
        if depth > 30:
            return {}
        if isinstance(node, dict):
            if "$ref" in node:
                name = node["$ref"].split("/")[-1]
                merged = {**defs.get(name, {}), **{k: v for k, v in node.items() if k != "$ref"}}
                return resolve(merged, depth + 1)
            return {k: resolve(v, depth + 1) for k, v in node.items() if k != "$defs"}
        if isinstance(node, list):
            return [resolve(v, depth + 1) for v in node]
        return node

    return resolve(schema)
