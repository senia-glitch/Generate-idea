"""База знаний и память: рабочая область прогона на диске.

Структура::

    <workspace>/
      reqpipe.toml          настройки прогона
      idea.md               исходная идея
      state.json            состояние конвейера
      decisions.jsonl       журнал решений на контрольных точках
      artifacts/<id>.vN.json  версии артефактов; <id>.json — последняя
      tasks/<id>.vN.md      задачи для агентов; schemas/<id>.json — схемы ответа
      results/<id>.json     сюда агент пишет ответ в режиме «агент ведёт конвейер»
      logs/                 сырые ответы исполнителей
      output/               SRS.md, requirements.json, tests/, prototype/, trace.json
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from reqpipe.core import Element, Instructions
from reqpipe.core.config import RunConfig

STATUSES = ("pending", "in_progress", "awaiting_approval", "awaiting_external", "done", "failed")


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class ElementState:
    status: str = "pending"
    version: int = 0                 # сколько версий артефакта сохранено
    runs: int = 0                    # сколько раз элементу выдавали задачу
    repairs: int = 0                 # попытки исправить ответ, не прошедший контракт
    feedback: list[dict] = field(default_factory=list)
    checkpoint: str = ""             # approval | loop_budget — что ждёт решения
    task_file: str = ""
    schema_file: str = ""
    result_file: str = ""
    plan: dict | None = None         # для внешнего этапа: план, ждущий результатов
    last_error: str = ""
    cost_usd: float = 0.0
    updated_at: str = ""


@dataclass
class RunState:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: str = field(default_factory=now)
    elements: dict[str, ElementState] = field(default_factory=dict)
    loop_counts: dict[str, int] = field(default_factory=dict)
    history: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    stopped: str = ""                # причина остановки, если конвейер остановлен

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "RunState":
        elements = {k: ElementState(**v) for k, v in data.get("elements", {}).items()}
        return cls(**{**{k: v for k, v in data.items() if k != "elements"}, "elements": elements})

    def log(self, event: str, element: str = "", **details: Any) -> None:
        self.history.append({"at": now(), "event": event, "element": element, **details})

    @property
    def total_cost(self) -> float:
        return round(sum(s.cost_usd for s in self.elements.values()), 4)


class Workspace:
    CONFIG = "reqpipe.toml"
    STATE = "state.json"
    IDEA = "idea.md"
    DECISIONS = "decisions.jsonl"

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    # ------------------------------------------------------------------ создание

    def exists(self) -> bool:
        return (self.root / self.STATE).exists()

    def init(self, idea_text: str, config: RunConfig, force: bool = False) -> None:
        if self.exists() and not force:
            raise FileExistsError(f"Рабочая область уже создана: {self.root}")
        for sub in ("artifacts", "tasks", "schemas", "results", "logs", "output"):
            (self.root / sub).mkdir(parents=True, exist_ok=True)
        self.write_text(self.IDEA, idea_text.strip() + "\n")
        self.save_config(config)
        self.save_state(RunState())

    # ------------------------------------------------------------------ файлы

    def path(self, rel: str) -> Path:
        return self.root / rel

    def write_text(self, rel: str, text: str) -> Path:
        target = self.path(rel)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-", suffix=target.suffix)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, target)
        return target

    def read_text(self, rel: str) -> str:
        return self.path(rel).read_text(encoding="utf-8")

    def write_json(self, rel: str, data: Any) -> Path:
        return self.write_text(rel, json.dumps(data, ensure_ascii=False, indent=2))

    def read_json(self, rel: str) -> Any:
        return json.loads(self.read_text(rel))

    def output_writer(self, rel: str, content: str) -> str:
        self.write_text(f"output/{rel}", content)
        return f"output/{rel}"

    # ------------------------------------------------------------------ настройки и состояние

    def load_config(self) -> RunConfig:
        return RunConfig.load(self.path(self.CONFIG))

    def save_config(self, config: RunConfig) -> None:
        self.write_text(self.CONFIG, config.to_toml())

    def idea_text(self) -> str:
        p = self.path(self.IDEA)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def load_state(self) -> RunState:
        p = self.path(self.STATE)
        return RunState.from_dict(json.loads(p.read_text(encoding="utf-8"))) if p.exists() else RunState()

    def save_state(self, state: RunState) -> None:
        self.write_json(self.STATE, state.to_dict())

    # ------------------------------------------------------------------ артефакты

    def save_artifact(self, element_id: str, version: int, data: dict) -> str:
        rel = f"artifacts/{element_id}.v{version}.json"
        self.write_json(rel, data)
        self.write_json(f"artifacts/{element_id}.json", data)
        return rel

    def load_artifact(self, element_id: str) -> dict | None:
        p = self.path(f"artifacts/{element_id}.json")
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

    def append_decision(self, decision: dict) -> None:
        p = self.path(self.DECISIONS)
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(decision, ensure_ascii=False) + "\n")

    def decisions(self) -> list[dict]:
        p = self.path(self.DECISIONS)
        if not p.exists():
            return []
        return [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines() if line.strip()]


ELEMENT = Element(
    id="kb", num="", title="База знаний и память", actor="RAG-хранилище артефактов", kind="infra", mode="service",
    instructions=Instructions(
        purpose=(
            "Общая память конвейера: агенты не теряют контекст между фазами, а каждый факт можно проверить по "
            "первоисточнику."
        ),
        methods=(
            "Векторный поиск (RAG) по исследованиям и артефактам",
            "Версионирование каждого артефакта",
            "Хранение источников и цитат для проверки фактов",
            "Единый глоссарий, общий для всех агентов",
        ),
        done="У каждого артефакта есть версия, агент-автор и ссылки на источники.",
    ),
)
