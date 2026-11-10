"""Публичные контракты домена «Формализация требований».

``SpecBundle`` — пакет спецификации: формируется на этапе 4.5 и дальше
передаётся по цепочке контрактов через все фильтры и согласование,
обогащаясь журналом проверок, рисками, решениями и приоритетами.
"""

from collections import defaultdict
from typing import Any, Literal

from pydantic import BaseModel, Field

from reqpipe.core import Artifact, TraceCatalog


# --------------------------------------------------------------------------- 4.1 Story Map

class Epic(BaseModel):
    id: str = Field(description="EP-001 …")
    title: str
    description: str = ""


class Story(BaseModel):
    id: str = Field(description="US-001 …")
    epic_id: str
    as_role: str
    i_want: str
    so_that: str
    persona_id: str = ""
    scenario_ids: list[str] = Field(default_factory=list)
    opportunity_ids: list[str] = Field(default_factory=list)
    pain_ids: list[str] = Field(default_factory=list)
    differentiator_ids: list[str] = Field(default_factory=list)
    is_differentiator: bool = False


class StoryMapDraft(BaseModel):
    epics: list[Epic]
    stories: list[Story]


class StoryMap(Artifact):
    epics: list[Epic]
    stories: list[Story]
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


# --------------------------------------------------------------------------- 4.2 модель данных

class Attribute(BaseModel):
    name: str
    type: str = "string"
    required: bool = True


class Relation(BaseModel):
    to: str = Field(description="ID связанной сущности ENT-…")
    kind: str = Field("1:N", description="1:1, 1:N, N:M")


class EntityModel(BaseModel):
    id: str = Field(description="ENT-… — тот же ID, что в онтологии домена")
    name: str
    attributes: list[Attribute] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


class Transition(BaseModel):
    from_state: str
    to_state: str
    event: str
    guard: str = ""


class StateMachine(BaseModel):
    entity_id: str
    states: list[str]
    transitions: list[Transition] = Field(default_factory=list)


class BusinessRule(BaseModel):
    id: str = Field(description="BR-001 …")
    statement: str = Field(description="Проверяемое условие")
    entity_ids: list[str] = Field(default_factory=list)


class UseCase(BaseModel):
    id: str = Field(description="UC-001 …")
    title: str
    actor: str = ""
    story_ids: list[str] = Field(default_factory=list)


class DataModelDraft(BaseModel):
    entities: list[EntityModel]
    state_machines: list[StateMachine] = Field(default_factory=list)
    rules: list[BusinessRule] = Field(default_factory=list)
    use_cases: list[UseCase] = Field(default_factory=list)
    diagrams: dict[str, str] = Field(default_factory=dict, description="Имя → диаграмма в Mermaid")


class DataModel(Artifact):
    entities: list[EntityModel]
    state_machines: list[StateMachine] = Field(default_factory=list)
    rules: list[BusinessRule] = Field(default_factory=list)
    use_cases: list[UseCase] = Field(default_factory=list)
    diagrams: dict[str, str] = Field(default_factory=dict)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


# --------------------------------------------------------------------------- 4.3 требования

Ears = Literal["ubiquitous", "event", "state", "unwanted", "optional", "complex"]


class Requirement(BaseModel):
    id: str = Field(description="FR-001 …")
    title: str
    statement: str = Field(description="Формулировка по EARS: «Когда <событие>, система должна <реакция>»")
    ears: Ears = "event"
    rationale: str = ""
    source_ids: list[str] = Field(default_factory=list, description="Откуда требование: US-…, OBL-…, PAIN-…")
    entity_ids: list[str] = Field(default_factory=list)
    rule_ids: list[str] = Field(default_factory=list)
    # заполняется на фазе 6
    feasible: bool | None = None
    size: str = ""
    kano: str = ""
    priority: str = ""
    release: str = ""
    status: Literal["draft", "approved"] = "draft"


class RequirementsDraft(BaseModel):
    requirements: list[Requirement]


class RequirementsRegistry(Artifact):
    schema_id: str = "reqpipe/requirements@1"
    requirements: list[Requirement]
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


# --------------------------------------------------------------------------- 4.4–4.5 приёмка и тесты

class AcceptanceScenario(BaseModel):
    id: str = Field(description="AC-001 …")
    requirement_id: str
    kind: Literal["positive", "negative", "boundary"] = "positive"
    title: str = ""
    gherkin: str = Field(description="Сценарий Given / When / Then (можно на русском: Дано / Когда / Тогда)")


class AcceptanceDraft(BaseModel):
    scenarios: list[AcceptanceScenario]


class AcceptanceSuite(Artifact):
    scenarios: list[AcceptanceScenario]
    requirements: list[Requirement] = Field(default_factory=list)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)


class CodeFile(BaseModel):
    path: str = Field(description="Относительный путь, например pages/login.page.ts")
    code: str


class AutoTest(BaseModel):
    id: str = Field(description="TC-001 …")
    scenario_id: str
    requirement_id: str
    title: str = ""
    file: str = Field(description="Относительный путь файла теста, например tests/fr-001.spec.ts")
    code: str


class AutoTestDraft(BaseModel):
    framework: Literal["playwright", "cypress"] = "playwright"
    page_objects: list[CodeFile] = Field(default_factory=list)
    tests: list[AutoTest]


class AutoTestRef(BaseModel):
    id: str
    scenario_id: str
    requirement_id: str
    file: str = ""


class GateLogEntry(BaseModel):
    gate: str
    element: str
    verdict: str
    summary: str = ""


class Risk(BaseModel):
    id: str = Field(description="RSK-001 …")
    description: str
    impact: Literal["low", "medium", "high"] = "medium"
    mitigation: str = ""
    source: str = ""


class DecisionRecord(BaseModel):
    id: str = Field(description="DEC-001 …")
    decision: str
    rationale: str = ""
    requirement_ids: list[str] = Field(default_factory=list)
    by: str = ""


class CoverageGap(BaseModel):
    kind: str
    id: str
    title: str = ""
    target: str = Field("", description="Кому дорабатывать: storymap или reqwriter")


class SpecBundle(BaseModel):
    requirements: list[Requirement] = Field(default_factory=list)
    scenarios: list[AcceptanceScenario] = Field(default_factory=list)
    tests: list[AutoTestRef] = Field(default_factory=list)
    catalog: TraceCatalog = Field(default_factory=TraceCatalog)
    gate_log: list[GateLogEntry] = Field(default_factory=list)
    risks: list[Risk] = Field(default_factory=list)
    decisions: list[DecisionRecord] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)
    architecture: dict[str, Any] = Field(default_factory=dict)
    benchmark: dict[str, Any] = Field(default_factory=dict)

    # ------------------------------------------------------------ трассировка

    def references(self) -> dict[str, set[str]]:
        """ID из каталога → требования, которые на него опираются (напрямую или через истории)."""
        index = {item.id: item for items in self.catalog.items.values() for item in items}
        refs: dict[str, set[str]] = defaultdict(set)
        for fr in self.requirements:
            frontier = list(fr.source_ids + fr.entity_ids + fr.rule_ids)
            seen: set[str] = set()
            while frontier:
                cur = frontier.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                refs[cur].add(fr.id)
                item = index.get(cur)
                if item is not None:
                    frontier.extend(item.refs)
        return refs

    def coverage_gaps(self, min_pain_severity: int = 4) -> list[CoverageGap]:
        """Детерминированная проверка полноты (используется фильтром G3)."""
        refs = self.references()
        gaps: list[CoverageGap] = []
        for kind, target, rule in (
            ("pain", "storymap", lambda i: (i.severity or 0) >= min_pain_severity),
            ("differentiator", "storymap", lambda i: True),
            ("story", "reqwriter", lambda i: True),
            ("obligation", "reqwriter", lambda i: True),
            ("entity", "reqwriter", lambda i: True),
        ):
            for item in self.catalog.get(kind):
                if rule(item) and not refs.get(item.id):
                    gaps.append(CoverageGap(kind=kind, id=item.id, title=item.title, target=target))
        with_scenarios = {s.requirement_id for s in self.scenarios}
        for fr in self.requirements:
            if fr.id not in with_scenarios:
                gaps.append(CoverageGap(kind="fr-without-scenario", id=fr.id, title=fr.title, target="reqwriter"))
        with_tests = {t.scenario_id for t in self.tests}
        for sc in self.scenarios:
            if sc.id not in with_tests:
                gaps.append(CoverageGap(kind="scenario-without-test", id=sc.id, title=sc.title, target="reqwriter"))
        return gaps

    def orphan_requirements(self) -> list[str]:
        """Требования без источника, известного каталогу."""
        known = {item.id for items in self.catalog.items.values() for item in items}
        return [fr.id for fr in self.requirements if not any(s in known for s in fr.source_ids)]

    def log_gate(self, gate: str, element: str, verdict: str, summary: str = "") -> "SpecBundle":
        self.gate_log = [g for g in self.gate_log if g.element != element]
        self.gate_log.append(GateLogEntry(gate=gate, element=element, verdict=verdict, summary=summary))
        return self


class AutoTestSuite(Artifact):
    framework: str = "playwright"
    files: list[str] = Field(default_factory=list, description="Записанные файлы тестов")
    spec: SpecBundle = Field(default_factory=SpecBundle)
