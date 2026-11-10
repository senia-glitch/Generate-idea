"""Настройки прогона (файл ``reqpipe.toml`` в рабочей области).

LLM по умолчанию не выбраны: пустое ``model`` означает «модель по умолчанию
в самом агенте» (Claude Code или OpenCode).
"""

from __future__ import annotations

import tomllib
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

EXECUTORS = ("manual", "claude-code", "opencode", "mock")


@dataclass
class ExecutorConfig:
    command: str = ""
    model: str = ""                 # пусто — модель по умолчанию в агенте
    extra_args: list[str] = field(default_factory=list)
    timeout_sec: int = 1800
    auto_approve: bool = False      # только OpenCode: --auto (разрешать инструменты без вопросов)
    fail_once: list[str] = field(default_factory=list)   # только mock: какие фильтры «падают» в первый раз


@dataclass
class ElementOverride:
    executor: str = ""
    model: str = ""
    extra_args: list[str] = field(default_factory=list)


def _default_executors() -> dict[str, ExecutorConfig]:
    return {
        "claude-code": ExecutorConfig(command="claude"),
        "opencode": ExecutorConfig(command="opencode"),
        "mock": ExecutorConfig(fail_once=["quality"]),
    }


@dataclass
class RunConfig:
    executor: str = "manual"
    autonomous: bool = False
    max_loop_iterations: int = 3
    max_repairs: int = 2
    context_budget_chars: int = 120_000
    parallel: int = 1
    arbiter: str = "rules"              # rules | executor
    arbiter_min_confidence: float = 0.7
    user_test_command: str = ""         # внешняя команда для немодерируемого теста (5.5)
    allow_waive_user_test: bool = False
    executors: dict[str, ExecutorConfig] = field(default_factory=_default_executors)
    elements: dict[str, ElementOverride] = field(default_factory=dict)

    # ---------------------------------------------------------------- выбор исполнителя

    def executor_for(self, element_id: str) -> str:
        override = self.elements.get(element_id)
        return (override.executor if override and override.executor else self.executor)

    def model_for(self, element_id: str, executor: str) -> str:
        override = self.elements.get(element_id)
        if override and override.model:
            return override.model
        cfg = self.executors.get(executor)
        return cfg.model if cfg else ""

    def extra_args_for(self, element_id: str, executor: str) -> list[str]:
        cfg = self.executors.get(executor)
        override = self.elements.get(element_id)
        return list(cfg.extra_args if cfg else []) + list(override.extra_args if override else [])

    # ---------------------------------------------------------------- (де)сериализация

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunConfig":
        run = data.get("run", {})
        cfg = cls(**{k: v for k, v in run.items() if k in cls.__dataclass_fields__ and k not in ("executors", "elements")})
        for name, raw in data.get("executor", {}).items():
            base = cfg.executors.get(name, ExecutorConfig())
            cfg.executors[name] = ExecutorConfig(**{**asdict(base), **raw})
        for name, raw in data.get("elements", {}).items():
            cfg.elements[name] = ElementOverride(**raw)
        if cfg.executor not in EXECUTORS:
            raise ValueError(f"Неизвестный исполнитель {cfg.executor!r}; допустимо: {', '.join(EXECUTORS)}")
        return cfg

    @classmethod
    def load(cls, path: Path) -> "RunConfig":
        if not path.exists():
            return cls()
        return cls.from_dict(tomllib.loads(path.read_text(encoding="utf-8")))

    def to_toml(self) -> str:
        lines = [
            "# Настройки прогона reqpipe. Пустая модель = модель по умолчанию в агенте.",
            "[run]",
            f'executor = "{self.executor}"          # manual | claude-code | opencode | mock',
            f"autonomous = {str(self.autonomous).lower()}         # true — решения на контрольных точках принимает агент-арбитр",
            f"max_loop_iterations = {self.max_loop_iterations}       # бюджет возвратов на каждую петлю доработки",
            f"max_repairs = {self.max_repairs}               # попыток исправить ответ агента, не прошедший контракт",
            f"context_budget_chars = {self.context_budget_chars}",
            f"parallel = {self.parallel}                  # сколько независимых этапов запускать одновременно",
            f'arbiter = "{self.arbiter}"             # rules | executor (арбитр-агент в автономном режиме)',
            f"arbiter_min_confidence = {self.arbiter_min_confidence}",
            f'user_test_command = "{_esc(self.user_test_command)}"      # команда немодерируемого теста: {{plan}} {{out}}',
            f"allow_waive_user_test = {str(self.allow_waive_user_test).lower()}",
            "",
        ]
        for name, ex in self.executors.items():
            lines += [
                f'[executor.{_key(name)}]',
                f'command = "{_esc(ex.command)}"',
                f'model = "{_esc(ex.model)}"',
                f"extra_args = {_list(ex.extra_args)}",
                f"timeout_sec = {ex.timeout_sec}",
            ]
            if name == "opencode":
                lines.append(f"auto_approve = {str(ex.auto_approve).lower()}")
            if name == "mock":
                lines.append(f"fail_once = {_list(ex.fail_once)}")
            lines.append("")
        lines.append("# Переопределения для отдельных элементов, например:")
        lines.append('# [elements.critic]\n# executor = "opencode"   # критик на другом агенте — независимая проверка')
        for name, ov in self.elements.items():
            lines += [
                f"[elements.{name}]",
                f'executor = "{_esc(ov.executor)}"',
                f'model = "{_esc(ov.model)}"',
                f"extra_args = {_list(ov.extra_args)}",
                "",
            ]
        return "\n".join(lines) + "\n"


def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _key(name: str) -> str:
    return f'"{name}"' if "-" in name else name


def _list(values: list[str]) -> str:
    return "[" + ", ".join(f'"{_esc(v)}"' for v in values) + "]"
