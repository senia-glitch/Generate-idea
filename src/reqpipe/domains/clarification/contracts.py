"""Публичные контракты домена «Прояснение замысла»."""

from pydantic import BaseModel, Field

from reqpipe.core import Artifact


class Assumption(BaseModel):
    id: str = Field(description="ASM-001, ASM-002 …")
    statement: str
    how_to_verify: str = ""


class QA(BaseModel):
    question: str
    answer: str
    is_assumption: bool = Field(False, description="true, если ответ — допущение, а не факт от автора")


class IdeaBrief(Artifact):
    goal: str
    problem: str
    target_audience: list[str] = Field(default_factory=list)
    context: str = ""
    constraints: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    qa_log: list[QA] = Field(default_factory=list, description="Вопросы 5W2H и ответы")


class Metric(BaseModel):
    name: str
    target: str


class ProblemStatement(Artifact):
    statement: str = Field(description="Проблема, сформулированная так, чтобы её можно было опровергнуть данными")
    who_suffers: str
    context: str = ""
    cost_of_problem: str = ""
    value_hypothesis: str
    success_metrics: list[Metric] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    lean_canvas: dict[str, str] = Field(default_factory=dict)
    # заполняется детерминированно из брифа — чтобы исследование видело аудиторию и допущения
    audience: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[Assumption] = Field(default_factory=list)


class ProblemStatementDraft(BaseModel):
    """То, что возвращает агент на этапе 1.2 (остальное дописывается из брифа)."""

    statement: str
    who_suffers: str
    context: str = ""
    cost_of_problem: str = ""
    value_hypothesis: str
    success_metrics: list[Metric] = Field(default_factory=list)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    lean_canvas: dict[str, str] = Field(default_factory=dict)
