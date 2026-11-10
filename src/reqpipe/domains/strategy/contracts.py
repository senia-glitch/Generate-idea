"""Публичные контракты домена «Синтез и стратегия»."""

from typing import Literal

from pydantic import BaseModel, Field

from reqpipe.core import Artifact, TraceCatalog
from reqpipe.domains.research.contracts import Competitor, FeatureRow


class Opportunity(BaseModel):
    id: str = Field(description="OPP-001 …")
    title: str
    description: str = ""
    pain_ids: list[str] = Field(default_factory=list)
    feature_ids: list[str] = Field(default_factory=list, description="Связанные строки матрицы функций FEAT-…")
    competitor_weaknesses: list[str] = Field(default_factory=list)
    errc: Literal["eliminate", "reduce", "raise", "create"] = "create"
    importance: int = Field(5, ge=1, le=10)
    satisfaction: int = Field(5, ge=1, le=10, description="Насколько текущие решения удовлетворяют потребность")
    score: float = Field(0, description="Opportunity Score; вычисляется автоматически")


class OpportunityDraft(BaseModel):
    opportunities: list[Opportunity]


class OpportunityMap(Artifact):
    opportunities: list[Opportunity]
    errc: dict[str, list[str]] = Field(default_factory=dict)
    competitors: list[Competitor] = Field(default_factory=list)
    feature_matrix: list[FeatureRow] = Field(default_factory=list)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


class Differentiator(BaseModel):
    id: str = Field(description="DIF-001 …")
    title: str
    description: str = ""
    opportunity_ids: list[str] = Field(default_factory=list)
    metric: str = ""
    target: str = ""


class SuperiorityCriterion(BaseModel):
    id: str = Field(description="SUP-001 …")
    criterion: str
    weight: float = Field(0.2, ge=0, le=1)
    measure: str = Field("", description="Как измеряем")
    our_target: str = ""
    competitor_baseline: str = ""


class ProductVisionDraft(BaseModel):
    positioning: str
    usp: str
    north_star_metric: str
    principles: list[str] = Field(default_factory=list)
    differentiators: list[Differentiator]
    superiority_criteria: list[SuperiorityCriterion]
    why_switch: str = Field(description="Почему пользователь конкурента перейдёт к нам")


class ProductVision(Artifact):
    positioning: str
    usp: str
    north_star_metric: str
    principles: list[str] = Field(default_factory=list)
    differentiators: list[Differentiator]
    superiority_criteria: list[SuperiorityCriterion]
    why_switch: str
    competitive_baseline: list[FeatureRow] = Field(default_factory=list)
    competitors: list[Competitor] = Field(default_factory=list)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


class Persona(BaseModel):
    id: str = Field(description="PER-001 …")
    name: str
    role: str = ""
    goals: list[str] = Field(default_factory=list)
    pain_ids: list[str] = Field(default_factory=list)
    skills: str = ""
    context: str = ""


class Role(BaseModel):
    id: str = Field(description="ROLE-001 …")
    name: str
    permissions: list[str] = Field(default_factory=list)


class JourneyStep(BaseModel):
    id: str = Field(description="CJS-001 …")
    stage: str
    action: str
    emotion: str = ""
    pain_ids: list[str] = Field(default_factory=list)


class Scenario(BaseModel):
    id: str = Field(description="SCN-001 …")
    title: str
    persona_id: str = ""
    kind: Literal["main", "alternative", "exception"] = "main"
    steps: list[str] = Field(default_factory=list)


class PersonasDraft(BaseModel):
    personas: list[Persona]
    roles: list[Role] = Field(default_factory=list)
    journey: list[JourneyStep] = Field(default_factory=list)
    scenarios: list[Scenario]


class PersonasAndScenarios(Artifact):
    personas: list[Persona]
    roles: list[Role] = Field(default_factory=list)
    journey: list[JourneyStep] = Field(default_factory=list)
    scenarios: list[Scenario]
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)
