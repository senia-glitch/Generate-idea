"""Публичные контракты домена «Каскад проверок качества».

Каждый фильтр публикует свой отчёт (``GateReport``) и передаёт дальше
пакет спецификации ``spec`` с отметкой о прохождении.
"""

from typing import Literal

from pydantic import BaseModel, Field

from reqpipe.core import FeedbackItem, GateReport
from reqpipe.domains.formalization.contracts import CoverageGap, Risk, SpecBundle


class _Draft(BaseModel):
    verdict: Literal["pass", "fail"]
    summary: str = ""
    findings: list[FeedbackItem] = Field(default_factory=list)


# --------------------------------------------------------------------------- G1

class RuleViolation(BaseModel):
    requirement_id: str
    rule: str
    fragment: str = ""


class RequirementScore(BaseModel):
    requirement_id: str
    necessity: int = Field(100, ge=0, le=100)
    unambiguity: int = Field(100, ge=0, le=100)
    atomicity: int = Field(100, ge=0, le=100)
    verifiability: int = Field(100, ge=0, le=100)
    feasibility: int = Field(100, ge=0, le=100)
    issues: list[str] = Field(default_factory=list)
    fix: str = Field("", description="Исправленная формулировка, если критерий нарушен")


class QualityDraft(_Draft):
    scores: list[RequirementScore] = Field(default_factory=list)


class QualityReport(GateReport):
    scores: list[RequirementScore] = Field(default_factory=list)
    rule_violations: list[RuleViolation] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- G2

class Contradiction(BaseModel):
    requirement_ids: list[str]
    explanation: str


class CriticDraft(_Draft):
    contradictions: list[Contradiction] = Field(default_factory=list)
    abuse_cases: list[str] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)


class CriticReport(GateReport):
    contradictions: list[Contradiction] = Field(default_factory=list)
    abuse_cases: list[str] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- G3

class TraceRow(BaseModel):
    source_id: str
    kind: str
    requirement_ids: list[str] = Field(default_factory=list)


class CoverageDraft(_Draft):
    semantic_gaps: list[CoverageGap] = Field(default_factory=list,
                                             description="Пробелы, которые не видны по ID: типовые функции домена и т. п.")


class CoverageReport(GateReport):
    matrix: list[TraceRow] = Field(default_factory=list)
    gaps: list[CoverageGap] = Field(default_factory=list)
    orphans: list[str] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- G4

class SimulationRun(BaseModel):
    persona_id: str
    scenario_id: str
    outcome: Literal["passed", "stuck"]
    stuck_at: str = Field("", description="ID требования, на котором персона застряла")
    notes: str = ""


class SimulationDraft(_Draft):
    runs: list[SimulationRun]


class SimulationReport(GateReport):
    runs: list[SimulationRun] = Field(default_factory=list)
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- G5

class UserTask(BaseModel):
    id: str = Field(description="UT-001 …")
    title: str
    scenario_id: str = ""
    requirement_ids: list[str] = Field(default_factory=list)


class UserTestPlan(BaseModel):
    """Что готовит агент: прототип и план теста."""

    prototype_html: str = Field(description="Самодостаточная HTML-страница кликабельного прототипа ключевых сценариев")
    tasks: list[UserTask]
    participant_profile: str = ""
    participants: int = Field(6, ge=1, le=50)


class SessionProblem(BaseModel):
    requirement_id: str = ""
    severity: Literal["critical", "major", "minor"] = "major"
    description: str


class UserSession(BaseModel):
    participant: str
    task_id: str
    success: bool
    time_sec: int = 0
    problems: list[SessionProblem] = Field(default_factory=list)


class UserTestResults(BaseModel):
    """Что приходит извне — от модератора или сервиса немодерируемого тестирования."""

    sessions: list[UserSession]
    synthetic: bool = Field(False, description="true — результаты не от реальных людей (mock)")
    source: str = ""


class UserTestReport(GateReport):
    plan: UserTestPlan
    results: UserTestResults | None = None
    waived: bool = False
    waiver_reason: str = ""
    prototype_path: str = ""
    spec: SpecBundle = Field(default_factory=SpecBundle)


# --------------------------------------------------------------------------- G6

class ParityItem(BaseModel):
    feature_id: str
    status: Literal["covered", "partial", "missing"]
    requirement_ids: list[str] = Field(default_factory=list)


class SuperiorityItem(BaseModel):
    criterion_id: str
    our_score: float = Field(ge=0, le=10)
    best_competitor_score: float = Field(ge=0, le=10)
    requirement_ids: list[str] = Field(default_factory=list)


class BenchmarkDraft(_Draft):
    parity: list[ParityItem]
    superiority: list[SuperiorityItem]
    why_switch_answer: str = ""


class BenchmarkScorecard(GateReport):
    parity: list[ParityItem] = Field(default_factory=list)
    superiority: list[SuperiorityItem] = Field(default_factory=list)
    weighted_ours: float = 0
    weighted_best_competitor: float = 0
    why_switch_answer: str = ""
    spec: SpecBundle = Field(default_factory=SpecBundle)
