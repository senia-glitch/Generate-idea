"""4.3 · Написание требований."""

from reqpipe.core import Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.formalization.contracts import DataModel, RequirementsDraft, RequirementsRegistry, StoryMap
from reqpipe.domains.research.contracts import VerifiedResearch


def finalize(ctx: Context, data: dict) -> dict:
    catalog = TraceCatalog.combine(
        ctx.input("storymap").get("catalog"), ctx.input("model").get("catalog"), ctx.input("factcheck").get("catalog"),
    )
    requirements = []
    for fr in data.get("requirements", []):
        requirements.append({**fr, "status": "draft"})
    return {"requirements": requirements, "catalog": catalog.model_dump()}


def example(ctx: Context) -> dict:
    stories = ctx.input("storymap").get("stories", [])
    entities = [e["id"] for e in ctx.input("model").get("entities", [])] or ["ENT-001"]
    rules = [r["id"] for r in ctx.input("model").get("rules", [])]
    obligations = ctx.input("factcheck").get("obligations", [])
    reqs = []
    for n, story in enumerate(stories, 1):
        reqs.append({
            "id": f"FR-{n:03d}", "title": story["i_want"][:60],
            "statement": f"Когда пользователь запускает сценарий «{story['i_want']}», система должна выполнить его "
                         f"без ручного ввода данных.",
            "ears": "event", "rationale": story.get("so_that", ""),
            "source_ids": [story["id"]] + story.get("pain_ids", []),
            "entity_ids": [entities[(n - 1) % len(entities)]], "rule_ids": rules[:1] if n == 1 else [],
        })
    for m, obl in enumerate(obligations, len(reqs) + 1):
        reqs.append({
            "id": f"FR-{m:03d}", "title": f"Соблюдение {obl['norm']}",
            "statement": f"Система должна {obl['requirement'].removeprefix('Система должна ').rstrip('.')}.",
            "ears": "ubiquitous", "rationale": f"Обязательство {obl['id']}", "source_ids": [obl["id"]],
            "entity_ids": entities[-1:],
        })
    if ctx.feedback:
        reqs[0]["rationale"] += " (уточнено по замечаниям фильтра)"
    return {"requirements": reqs}


ELEMENT = Element(
    id="reqwriter", num="4.3", title="Написание требований", actor="Агент-аналитик требований", kind="agent",
    instructions=Instructions(
        purpose=(
            "Создать формальную спецификацию: каждое требование описывает одно проверяемое поведение системы и "
            "имеет явное происхождение."
        ),
        methods=(
            "Шаблоны EARS: «Когда <событие>, система должна <реакция>», «Пока <состояние>…», «Если <нежелательное>, то…»",
            "Атрибуты: ID, приоритет, источник, обоснование, владелец",
            "Учёт обязательств из реестра комплаенса",
            "Ссылки на сущности модели данных",
            "Требования ведутся как структурированные данные по единой схеме (JSON / YAML: ID, тип, источник, связи, "
            "статус, версия), а не как свободный текст — так полноту и противоречия можно проверять машинно, а сотни "
            "требований не теряются между частями контекста",
        ),
        prompt=(
            "Одно требование — одно поведение. Запрещены слова «быстро», «удобно», «и т. д.», «при необходимости». "
            "Всегда указывай источник требования."
        ),
        done="Каждая история и каждое обязательство комплаенса превращены в требования с полным набором атрибутов.",
    ),
    consumes=(
        Consumes("storymap", StoryMap),
        Consumes("model", DataModel),
        Consumes("factcheck", VerifiedResearch, ("obligations", "catalog"), note="обязательные требования"),
    ),
    output=RequirementsRegistry,
    agent_output=RequirementsDraft,
    finalize=finalize,
    example=example,
)
