"""3.1 · Gap-анализ и поиск возможностей."""

from reqpipe.core import CatalogItem, Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.research.contracts import VerifiedResearch
from reqpipe.domains.strategy.contracts import OpportunityDraft, OpportunityMap


def opportunity_score(importance: int, satisfaction: int) -> float:
    """Opportunity Score (Ulwick): важность + max(важность − удовлетворённость, 0)."""
    return float(importance + max(importance - satisfaction, 0))


def finalize(ctx: Context, data: dict) -> dict:
    research = ctx.input("factcheck")
    opportunities = []
    errc: dict[str, list[str]] = {"eliminate": [], "reduce": [], "raise": [], "create": []}
    for opp in data.get("opportunities", []):
        opp = {**opp, "score": opportunity_score(opp.get("importance", 5), opp.get("satisfaction", 5))}
        opportunities.append(opp)
        errc.setdefault(opp.get("errc", "create"), []).append(opp["id"])
    opportunities.sort(key=lambda o: o["score"], reverse=True)
    catalog = TraceCatalog.combine(research.get("catalog"))
    catalog.add("opportunity", [CatalogItem(id=o["id"], title=o["title"], severity=round(o["score"]),
                                            refs=o.get("pain_ids", []) + o.get("feature_ids", []))
                                for o in opportunities])
    return {
        "opportunities": opportunities,
        "errc": errc,
        "competitors": research.get("competitors", []),
        "feature_matrix": research.get("feature_matrix", []),
        "catalog": catalog.model_dump(),
    }


def example(ctx: Context) -> dict:
    research = ctx.input("factcheck")
    pains = sorted(research.get("pains", []), key=lambda p: -p.get("severity", 0))
    features = research.get("feature_matrix", [])
    opps = []
    for n, pain in enumerate(pains[:2], 1):
        opps.append({
            "id": f"OPP-{n:03d}", "title": f"Решить: {pain['title']}",
            "description": "Конкуренты закрывают эту боль слабо или вручную",
            "pain_ids": [pain["id"]], "feature_ids": [features[min(n, len(features)) - 1]["id"]] if features else [],
            "competitor_weaknesses": ["Сложный интерфейс"], "errc": "create" if n == 1 else "raise",
            "importance": 9 - n, "satisfaction": 3,
        })
    return {"opportunities": opps}


ELEMENT = Element(
    id="gap", num="3.1", title="Gap-анализ и поиск возможностей", actor="Агент-стратег", kind="agent",
    instructions=Instructions(
        purpose=(
            "Найти точки, где можно стать лучше рынка: незакрытые потребности, плохо реализованные функции, "
            "лишняя сложность у конкурентов."
        ),
        methods=(
            "Наложение карты болей на матрицу функций конкурентов",
            "Сетка ERRC из стратегии «голубого океана»: упразднить, снизить, повысить, создать",
            "Opportunity Score: важность × неудовлетворённость",
        ),
        prompt=(
            "Ищи не только недостающие функции, но и то, что конкуренты делают избыточно сложно. "
            "Каждую возможность обоснуй данными фазы 2."
        ),
        done=(
            "Каждая возможность связана с болями и конкретными слабостями конкурентов и имеет оценку потенциала."
        ),
    ),
    consumes=(Consumes("factcheck", VerifiedResearch, ("competitors", "feature_matrix", "pains", "jobs", "catalog"),
                       note="матрица функций и карта болей"),),
    output=OpportunityMap,
    agent_output=OpportunityDraft,
    finalize=finalize,
    example=example,
)
