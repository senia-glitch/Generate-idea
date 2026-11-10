"""Публичные контракты домена «Приоритизация и согласование»."""

from typing import Literal

from pydantic import BaseModel, Field

from reqpipe.core import Artifact, FeedbackItem, GateReport
from reqpipe.domains.formalization.contracts import DecisionRecord, Risk, SpecBundle

Size = Literal["XS", "S", "M", "L", "XL"]
SIZE_EFFORT = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}


# --------------------------------------------------------------------------- 6.1

class ArchitectureSketch(BaseModel):
    components: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    data_stores: list[str] = Field(default_factory=list)


class FeasibilityItem(BaseModel):
    requirement_id: str
    feasible: bool = True
    size: Size = "M"
    risk: str = ""
    alternative: str = Field("", description="Реализуемая альтернатива, если требование невыполнимо")


class FeasibilityDraft(BaseModel):
    verdict: Literal["pass", "fail"]
    summary: str = ""
    findings: list[FeedbackItem] = Field(default_factory=list)
    architecture: ArchitectureSketch = Field(default_factory=ArchitectureSketch)
    items: list[FeasibilityItem]
    risks: list[Risk] = Field(default_factory=list)


class FeasibilityReport(GateReport):
    architecture: ArchitectureSketch = Field(default_factory=ArchitectureSketch)
    items: list[FeasibilityItem] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- 6.2

class BacklogItem(BaseModel):
    requirement_id: str
    kano: Literal["must", "performance", "attractive", "indifferent"] = "performance"
    reach: float = Field(100, ge=0, description="Сколько пользователей затронет за период")
    impact: float = Field(1, ge=0, le=3, description="0.25 … 3")
    confidence: float = Field(0.8, ge=0, le=1)
    effort: float = Field(0, ge=0, description="Человеко-недели; 0 — взять из оценки размера 6.1")
    rice: float = 0
    moscow: Literal["must", "should", "could", "wont"] = "should"
    release: str = Field("MVP", description="MVP, R2, R3 …")


class BacklogDraft(BaseModel):
    items: list[BacklogItem]
    mvp_rationale: str
    wont_have_rationale: str = ""


class PrioritizedBacklog(Artifact):
    items: list[BacklogItem]
    mvp_rationale: str
    wont_have_rationale: str = ""
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- 6.3

class Position(BaseModel):
    role: str
    stance: str


class Conflict(BaseModel):
    id: str = Field(description="CNF-001 …")
    topic: str
    positions: list[Position] = Field(default_factory=list)
    resolution: str = ""
    resolved_by: Literal["consensus", "moderator", "escalated"] = "consensus"
    requirement_ids: list[str] = Field(default_factory=list)


class ScopeRevision(BaseModel):
    needed: bool = False
    reason: str = ""


class DebateDraft(BaseModel):
    conflicts: list[Conflict] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    escalations: list[str] = Field(default_factory=list, description="Вопросы, которые не удалось решить консенсусом")
    scope_revision: ScopeRevision = Field(default_factory=ScopeRevision)


class DebateProtocol(Artifact):
    conflicts: list[Conflict] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    escalations: list[str] = Field(default_factory=list)
    scope_revision: ScopeRevision = Field(default_factory=ScopeRevision)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- 6.4

class SignoffDraft(BaseModel):
    executive_summary: str
    changes: list[str] = Field(default_factory=list)
    disputed_points: list[str] = Field(default_factory=list)
    risks_summary: str = ""


class Baseline(Artifact):
    version: str = "v1.0"
    executive_summary: str
    changes: list[str] = Field(default_factory=list)
    disputed_points: list[str] = Field(default_factory=list)
    risks_summary: str = ""
    conditions: dict[str, bool] = Field(default_factory=dict)
    approved: bool = False
    approved_by: str = ""
    approved_at: str = ""
    low_confidence_decisions: list[str] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)
