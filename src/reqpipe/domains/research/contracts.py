"""Публичные контракты домена «Исследование»."""

from typing import Literal

from pydantic import BaseModel, Field

from reqpipe.core import Artifact, FeedbackItem, GateReport, Source, TraceCatalog

Depth = Literal["none", "basic", "good", "excellent"]


class Fact(BaseModel):
    id: str = Field(description="FCT-CMP-001, FCT-VOC-001, FCT-DOM-001, FCT-LAW-001 …")
    claim: str = Field(description="Проверяемое утверждение")
    sources: list[Source] = Field(default_factory=list)


class Competitor(BaseModel):
    id: str = Field(description="CMP-001 …")
    name: str
    kind: Literal["direct", "indirect", "workaround"] = "direct"
    url: str = ""
    pricing: str = ""
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class FeatureRow(BaseModel):
    id: str = Field(description="FEAT-001 …")
    name: str
    user_value: str = ""
    coverage: dict[str, Depth] = Field(default_factory=dict, description="ID конкурента → глубина реализации")


class CompetitorAnalysis(Artifact):
    competitors: list[Competitor]
    feature_matrix: list[FeatureRow]
    facts: list[Fact] = Field(default_factory=list)


class Pain(BaseModel):
    id: str = Field(description="PAIN-001 …")
    title: str
    situation: str = Field("", description="Конкретная ситуация, где продукт подвёл пользователя")
    frequency: int = Field(3, ge=1, le=5)
    severity: int = Field(3, ge=1, le=5)
    segments: list[str] = Field(default_factory=list)
    evidence: list[Source] = Field(default_factory=list)


class Job(BaseModel):
    id: str = Field(description="JTBD-001 …")
    when: str
    want: str
    so_that: str
    pain_ids: list[str] = Field(default_factory=list)


class VoiceOfCustomer(Artifact):
    pains: list[Pain]
    jobs: list[Job] = Field(default_factory=list)
    feature_requests: list[str] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)


class Term(BaseModel):
    term: str
    definition: str
    example: str = ""
    ambiguous: bool = False


class Entity(BaseModel):
    id: str = Field(description="ENT-001 …")
    name: str
    description: str = ""
    attributes: list[str] = Field(default_factory=list)


class Process(BaseModel):
    id: str = Field(description="PRC-001 …")
    name: str
    actors: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class DomainAnalysis(Artifact):
    glossary: list[Term]
    entities: list[Entity]
    processes: list[Process] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)


class Obligation(BaseModel):
    id: str = Field(description="OBL-001 …")
    norm: str = Field(description="Название нормы: закон, стандарт")
    jurisdiction: str
    requirement: str = Field(description="Что конкретно система обязана делать или не делать")
    source: Source = Field(default_factory=Source)


class ComplianceRegistry(Artifact):
    obligations: list[Obligation]
    facts: list[Fact] = Field(default_factory=list)


class FactStatus(BaseModel):
    fact_id: str
    status: Literal["confirmed", "hypothesis", "refuted"]
    confidence: float = Field(0.8, ge=0, le=1)
    evidence: list[Source] = Field(default_factory=list)
    note: str = ""


class FactCheckResult(BaseModel):
    """Ответ агента-фактчекера (остальное собирается детерминированно)."""

    verdict: Literal["pass", "fail"]
    summary: str = ""
    findings: list[FeedbackItem] = Field(default_factory=list)
    statuses: list[FactStatus]


class VerifiedResearch(GateReport):
    """Проверенная база фактов: всё, что исследование передаёт дальше."""

    statuses: list[FactStatus] = Field(default_factory=list)
    hypotheses: list[str] = Field(default_factory=list, description="Утверждения, принятые как гипотезы")
    competitors: list[Competitor] = Field(default_factory=list)
    feature_matrix: list[FeatureRow] = Field(default_factory=list)
    pains: list[Pain] = Field(default_factory=list)
    jobs: list[Job] = Field(default_factory=list)
    glossary: list[Term] = Field(default_factory=list)
    entities: list[Entity] = Field(default_factory=list)
    processes: list[Process] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)
