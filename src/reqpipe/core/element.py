"""Элемент — одна карточка эталонной схемы.

Элемент описывает:
* что он потребляет (``consumes``) и что публикует (``output``);
* инструкции для агента (взяты с карточки эталонной схемы);
* необязательные детерминированные шаги: ``run`` (элемент без агента),
  ``finalize`` (обогащение результата агента), ``evaluate`` (решение фильтра),
  ``example`` (эталонный результат для mock-исполнителя и тестов).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable, Literal

from pydantic import BaseModel

from reqpipe.core.contracts import Artifact, Consumes, FeedbackItem, Loop

if TYPE_CHECKING:  # pragma: no cover
    from reqpipe.core.config import RunConfig

Kind = Literal["input", "agent", "skill", "multi", "human", "output", "infra"]
Mode = Literal["agent", "deterministic", "external", "service"]
Capability = Literal["web", "code", "files"]


@dataclass(frozen=True)
class Instructions:
    """Текст карточки: назначение, методы, ключевая инструкция, критерий готовности."""

    purpose: str
    methods: tuple[str, ...] = ()
    prompt: str = ""
    done: str = ""
    hitl: str = ""          # роль человека (режим с человеком в контуре)
    auto_note: str = ""     # что меняется в автономном режиме
    auto_prompt: str = ""   # инструкция агенту в автономном режиме (если отличается)


@dataclass
class GateOutcome:
    """Решение фильтра: пройден ли он и кому что вернуть на доработку."""

    passed: bool
    feedback: dict[str, list[FeedbackItem]] = field(default_factory=dict)
    summary: str = ""


@dataclass
class Context:
    """Всё, что элемент видит во время работы: только данные по своим контрактам."""

    element: "Element"
    inputs: dict[str, dict[str, Any]]          # source_id -> данные по контракту
    feedback: list[FeedbackItem] = field(default_factory=list)
    iteration: int = 0                          # сколько раз элемент уже перезапускали
    loop_counts: dict[str, int] = field(default_factory=dict)  # "src->dst" -> возвратов
    autonomous: bool = False
    config: "RunConfig | None" = None
    idea_text: str = ""
    output_writer: Callable[[str, str], str] | None = None

    def write_output(self, relpath: str, content: str) -> str:
        """Записать файл в папку output рабочей области (тесты, прототип, SRS)."""
        if self.output_writer is None:
            return relpath
        return self.output_writer(relpath, content)

    def input(self, source: str) -> dict[str, Any]:
        return self.inputs.get(source, {})


@dataclass
class Element:
    id: str
    num: str
    title: str
    actor: str
    kind: Kind
    instructions: Instructions
    output: type[Artifact] | None = None
    agent_output: type[BaseModel] | None = None   # что возвращает агент (по умолчанию = output)
    consumes: tuple[Consumes, ...] = ()
    loops: tuple[Loop, ...] = ()
    gate: str | None = None
    checkpoint: bool = False                      # нужна контрольная точка (человек или арбитр)
    mode: Mode = "agent"
    capabilities: frozenset[str] = frozenset()
    run: Callable[[Context], dict[str, Any]] | None = None
    prepare: Callable[[Context], dict[str, Any]] | None = None      # детерминированные проверки до агента
    finalize: Callable[[Context, dict[str, Any]], dict[str, Any]] | None = None
    evaluate: Callable[[Context, dict[str, Any]], GateOutcome] | None = None
    on_approve: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]] | None = None
    example: Callable[[Context], dict[str, Any]] | None = None
    # внешний этап (тест с людьми): агент готовит план, результаты приходят извне
    external_model: type[BaseModel] | None = None
    on_plan: Callable[[Context, dict[str, Any]], dict[str, Any]] | None = None
    example_results: Callable[[Context, dict[str, Any]], dict[str, Any]] | None = None
    domain: str = ""

    @property
    def response_model(self) -> type[BaseModel] | None:
        """Модель, по которой проверяется ответ агента."""
        return self.agent_output or self.output

    @property
    def is_gate_like(self) -> bool:
        return bool(self.gate) or bool(self.loops)

    @property
    def loop_targets(self) -> tuple[str, ...]:
        return tuple(l.target for l in self.loops)

    def default_loop_target(self) -> str | None:
        return self.loops[0].target if self.loops else None
