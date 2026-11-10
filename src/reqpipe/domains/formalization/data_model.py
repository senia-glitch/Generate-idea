"""4.2 · Модель данных и поведения."""

from reqpipe.core import CatalogItem, Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.formalization.contracts import DataModel, DataModelDraft
from reqpipe.domains.research.contracts import VerifiedResearch


def finalize(ctx: Context, data: dict) -> dict:
    catalog = TraceCatalog.combine(ctx.input("factcheck").get("catalog"))
    catalog.add("entity", [CatalogItem(id=e["id"], title=e["name"], refs=[r["to"] for r in e.get("relations", [])])
                           for e in data.get("entities", [])])
    catalog.add("rule", [CatalogItem(id=r["id"], title=r["statement"], refs=r.get("entity_ids", []))
                         for r in data.get("rules", [])])
    return {**data, "catalog": catalog.model_dump()}


def example(ctx: Context) -> dict:
    entities = ctx.input("factcheck").get("entities", [])
    first = entities[0]["id"] if entities else "ENT-001"
    return {
        "entities": [
            {"id": e["id"], "name": e["name"],
             "attributes": [{"name": a, "type": "string", "required": True} for a in e.get("attributes", [])],
             "relations": [] if e["id"] == first else [{"to": first, "kind": "1:N"}]}
            for e in entities
        ],
        "state_machines": [{"entity_id": first, "states": ["черновик", "подтверждена", "архив"],
                            "transitions": [{"from_state": "черновик", "to_state": "подтверждена", "event": "подтвердить"},
                                            {"from_state": "подтверждена", "to_state": "архив", "event": "архивировать"}]}],
        "rules": [{"id": "BR-001", "statement": "Сумма записи больше нуля", "entity_ids": [first]}],
        "use_cases": [{"id": "UC-001", "title": "Импорт записей", "actor": "Пользователь"}],
        "diagrams": {"er": "erDiagram\n  RECORD ||--o{ REPORT : входит"},
    }


ELEMENT = Element(
    id="model", num="4.2", title="Модель данных и поведения", actor="Агент-системный аналитик", kind="agent",
    capabilities=frozenset({"code"}),
    instructions=Instructions(
        purpose=(
            "Дать требованиям строгий каркас: что хранит система, какие состояния проходят объекты и какие "
            "правила действуют."
        ),
        methods=(
            "Концептуальная ER-модель на основе онтологии домена",
            "Конечные автоматы для ключевых объектов",
            "Каталог бизнес-правил и вычислений",
            "Диаграммы вариантов использования (Use Case)",
        ),
        prompt=(
            "Для каждой сущности перечисли все состояния и допустимые переходы. "
            "Каждое правило запиши как проверяемое условие."
        ),
        done="Каждая сущность и каждый переход состояния покрыты хотя бы одной историей.",
    ),
    consumes=(Consumes("factcheck", VerifiedResearch, ("glossary", "entities", "processes", "catalog"),
                       note="онтология домена"),),
    output=DataModel,
    agent_output=DataModelDraft,
    finalize=finalize,
    example=example,
)
