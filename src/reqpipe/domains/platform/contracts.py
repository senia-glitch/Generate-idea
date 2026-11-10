"""Публичные контракты сквозного слоя."""

from typing import Any, Literal

from pydantic import BaseModel, Field

from reqpipe.core import Artifact


class ContextPack(Artifact):
    element_id: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    truncated: list[str] = Field(default_factory=list, description="Что сокращено и где лежит полный текст")
    size_chars: int = 0
    budget_chars: int = 0


class TraceNode(BaseModel):
    id: str
    kind: str
    title: str = ""


class TraceEdge(BaseModel):
    source: str
    target: str
    kind: str = "refs"


class TraceGraph(Artifact):
    nodes: list[TraceNode] = Field(default_factory=list)
    edges: list[TraceEdge] = Field(default_factory=list)


class CheckpointDecision(Artifact):
    element_id: str
    kind: Literal["approval", "loop_budget", "external_waiver"] = "approval"
    decision: Literal["approve", "reject", "waive", "stop"]
    by: Literal["human", "arbiter"]
    comment: str = ""
    confidence: float | None = None
    low_confidence: bool = False
    at: str = ""


class ArbiterVerdict(BaseModel):
    """Ответ агента-арбитра (режим arbiter = executor)."""

    decision: Literal["approve", "reject"]
    confidence: float = Field(ge=0, le=1)
    rationale: str
