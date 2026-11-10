"""4.1 · Декомпозиция и Story Map."""

from reqpipe.core import CatalogItem, Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.formalization.contracts import StoryMap, StoryMapDraft
from reqpipe.domains.strategy.contracts import PersonasAndScenarios, ProductVision

VISION_FIELDS = ("positioning", "usp", "north_star_metric", "principles", "differentiators",
                 "superiority_criteria", "why_switch", "catalog")


def finalize(ctx: Context, data: dict) -> dict:
    catalog = TraceCatalog.combine(ctx.input("vision").get("catalog"), ctx.input("personas").get("catalog"))
    catalog.add("epic", [CatalogItem(id=e["id"], title=e["title"]) for e in data.get("epics", [])])
    catalog.add("story", [
        CatalogItem(id=s["id"], title=s.get("i_want", ""),
                    refs=s.get("pain_ids", []) + s.get("opportunity_ids", []) + s.get("differentiator_ids", [])
                    + s.get("scenario_ids", []) + ([s["persona_id"]] if s.get("persona_id") else []))
        for s in data.get("stories", [])
    ])
    return {**data, "catalog": catalog.model_dump()}


def example(ctx: Context) -> dict:
    vision, personas = ctx.input("vision"), ctx.input("personas")
    catalog = TraceCatalog.combine(vision.get("catalog"))
    pains = [p for p in catalog.get("pain") if (p.severity or 0) >= 4]
    difs = vision.get("differentiators", [])
    scenarios = personas.get("scenarios", [])
    stories = []
    for n, pain in enumerate(pains, 1):
        dif = difs[(n - 1) % len(difs)] if difs else None
        stories.append({
            "id": f"US-{n:03d}", "epic_id": "EP-001", "as_role": "пользователь",
            "i_want": f"чтобы проблема «{pain.title}» решалась автоматически", "so_that": "экономить время",
            "persona_id": "PER-001", "scenario_ids": [scenarios[(n - 1) % len(scenarios)]["id"]] if scenarios else [],
            "opportunity_ids": dif["opportunity_ids"] if dif else [], "pain_ids": [pain.id],
            "differentiator_ids": [dif["id"]] if dif else [], "is_differentiator": bool(dif),
        })
    stories.append({"id": f"US-{len(stories) + 1:03d}", "epic_id": "EP-002", "as_role": "администратор",
                    "i_want": "выгружать отчёт", "so_that": "делиться итогами с командой", "persona_id": "PER-002"})
    return {
        "epics": [{"id": "EP-001", "title": "Данные без ручного ввода"}, {"id": "EP-002", "title": "Отчёты"}],
        "stories": stories,
    }


ELEMENT = Element(
    id="storymap", num="4.1", title="Декомпозиция и Story Map", actor="Агент-продакт", kind="agent",
    instructions=Instructions(
        purpose=(
            "Перейти от стратегии к структуре продукта: каждая история связана с персоной, сценарием и "
            "возможностью."
        ),
        methods=(
            "User Story Mapping",
            "Истории в формате «Как <роль>, я хочу <действие>, чтобы <ценность>»",
            "Иерархия: эпик → функция → история",
            "Отметка историй-дифференциаторов",
        ),
        prompt="Не пропусти «скучные» истории: регистрацию, настройки, уведомления, ошибки, администрирование.",
        done="Каждый этап CJM покрыт историями; у каждой истории есть источник.",
    ),
    consumes=(
        Consumes("vision", ProductVision, VISION_FIELDS),
        Consumes("personas", PersonasAndScenarios),
    ),
    output=StoryMap,
    agent_output=StoryMapDraft,
    finalize=finalize,
    example=example,
)
