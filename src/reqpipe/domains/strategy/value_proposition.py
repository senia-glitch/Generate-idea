"""3.2 · Ценностное предложение и критерии превосходства."""

from reqpipe.core import CatalogItem, Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.strategy.contracts import OpportunityMap, ProductVision, ProductVisionDraft


def finalize(ctx: Context, data: dict) -> dict:
    gap = ctx.input("gap")
    criteria = data.get("superiority_criteria", [])
    total = sum(c.get("weight", 0) for c in criteria) or 1.0
    criteria = [{**c, "weight": round(c.get("weight", 0) / total, 3)} for c in criteria]   # веса в сумме = 1
    catalog = TraceCatalog.combine(gap.get("catalog"))
    catalog.add("differentiator", [CatalogItem(id=d["id"], title=d["title"], refs=d.get("opportunity_ids", []))
                                   for d in data.get("differentiators", [])])
    catalog.add("criterion", [CatalogItem(id=c["id"], title=c["criterion"], data={"weight": c["weight"]})
                              for c in criteria])
    return {
        **data,
        "superiority_criteria": criteria,
        "competitive_baseline": gap.get("feature_matrix", []),
        "competitors": gap.get("competitors", []),
        "catalog": catalog.model_dump(),
    }


def example(ctx: Context) -> dict:
    opps = ctx.input("gap").get("opportunities", [])
    return {
        "positioning": "Для занятых пользователей, которым важна точность, — сервис без ручного ввода",
        "usp": "Данные попадают в систему сами и проверяются автоматически",
        "north_star_metric": "Доля записей, внесённых без ручного ввода",
        "principles": ["Ноль ручного ввода", "Каждая цифра проверяема"],
        "differentiators": [
            {"id": f"DIF-{n:03d}", "title": o["title"], "opportunity_ids": [o["id"]],
             "metric": "Время на задачу", "target": "в 2 раза быстрее конкурента А"}
            for n, o in enumerate(opps[:2], 1)
        ],
        "superiority_criteria": [
            {"id": "SUP-001", "criterion": "Время на ключевую задачу", "weight": 0.6, "measure": "минуты",
             "our_target": "≤ 5 мин", "competitor_baseline": "15 мин"},
            {"id": "SUP-002", "criterion": "Ошибки в итогах", "weight": 0.4, "measure": "% записей с ошибкой",
             "our_target": "< 1%", "competitor_baseline": "5%"},
        ],
        "why_switch": "Потому что у нас данные вводить не нужно, а у конкурента — каждую неделю",
    }


ELEMENT = Element(
    id="vision", num="3.2", title="Ценностное предложение", actor="Скилл Product Vision", kind="skill",
    checkpoint=True,
    instructions=Instructions(
        purpose=(
            "Выбрать стратегию превосходства и превратить её в ограниченный набор ключевых дифференциаторов, "
            "которые затем станут «вау»-требованиями."
        ),
        methods=(
            "Value Proposition Canvas",
            "Формула позиционирования: для кого, какую задачу решаем, чем отличаемся",
            "North Star Metric",
            "От трёх до пяти ключевых дифференциаторов",
            "Критерии превосходства фиксируются здесь, до написания требований: в чём именно и насколько система "
            "должна быть лучше конкурентов. По ним же выносит вердикт финальный бенчмарк (G6), поэтому планку "
            "нельзя сдвинуть задним числом",
        ),
        prompt=(
            "Сформулируй, почему пользователь конкурента перейдёт к нам. "
            "Если ответ звучит как «то же самое, но лучше» — ищи сильнее."
        ),
        done=(
            "Дифференциаторы измеримы, подтверждены возможностями из 3.1 и одобрены автором идеи; "
            "критерии превосходства зафиксированы."
        ),
        hitl="Автор идеи утверждает выбранную стратегию дифференциации.",
        auto_note=(
            "Стратегию утверждает агент-арбитр: дифференциаторы должны быть подтверждены возможностями из 3.1 "
            "и измеримы, иначе — возврат на доработку."
        ),
    ),
    consumes=(Consumes("gap", OpportunityMap),),
    output=ProductVision,
    agent_output=ProductVisionDraft,
    finalize=finalize,
    example=example,
)
