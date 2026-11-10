"""2.5 · G0 Верификация фактов.

Агент возвращает только статусы утверждений; проверенная база фактов,
которую получают следующие фазы, собирается детерминированно.
Доработка уходит тому исследовательскому агенту, чей факт не подтвердился
(на эталонной схеме нарисована петля к 2.1; к 2.2–2.4 — уточнение).
"""

from reqpipe.core import CatalogItem, Consumes, Context, Element, FeedbackItem, Instructions, Loop, TraceCatalog
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.research.contracts import (
    ComplianceRegistry,
    CompetitorAnalysis,
    DomainAnalysis,
    FactCheckResult,
    VerifiedResearch,
    VoiceOfCustomer,
)

ORIGINS = ("competitors", "voc", "domain", "compliance")


def _fact_origins(ctx: Context) -> dict[str, str]:
    return {f["id"]: src for src in ORIGINS for f in ctx.input(src).get("facts", [])}


def finalize(ctx: Context, data: dict) -> dict:
    origins = _fact_origins(ctx)
    statuses = {s["fact_id"]: s for s in data.get("statuses", [])}
    for fact_id in origins:
        statuses.setdefault(fact_id, {"fact_id": fact_id, "status": "hypothesis", "confidence": 0.0,
                                      "note": "Статус не указан фактчекером — принято как гипотеза"})
    claims = {f["id"]: f["claim"] for src in ORIGINS for f in ctx.input(src).get("facts", [])}
    cmp_, voc, dom, law = (ctx.input(s) for s in ORIGINS)

    catalog = TraceCatalog()
    catalog.add("competitor", [CatalogItem(id=c["id"], title=c["name"]) for c in cmp_.get("competitors", [])])
    catalog.add("feature", [CatalogItem(id=f["id"], title=f["name"], data={"coverage": f.get("coverage", {})})
                            for f in cmp_.get("feature_matrix", [])])
    catalog.add("pain", [CatalogItem(id=p["id"], title=p["title"], severity=p.get("severity"))
                         for p in voc.get("pains", [])])
    catalog.add("job", [CatalogItem(id=j["id"], title=j.get("want", ""), refs=j.get("pain_ids", []))
                        for j in voc.get("jobs", [])])
    catalog.add("entity", [CatalogItem(id=e["id"], title=e["name"]) for e in dom.get("entities", [])])
    catalog.add("obligation", [CatalogItem(id=o["id"], title=o["requirement"], severity=5)
                               for o in law.get("obligations", [])])
    return {
        **data,
        "statuses": list(statuses.values()),
        "hypotheses": [claims.get(k, k) for k, s in statuses.items() if s["status"] == "hypothesis"],
        "competitors": cmp_.get("competitors", []),
        "feature_matrix": cmp_.get("feature_matrix", []),
        "pains": voc.get("pains", []),
        "jobs": voc.get("jobs", []),
        "glossary": dom.get("glossary", []),
        "entities": dom.get("entities", []),
        "processes": dom.get("processes", []),
        "obligations": law.get("obligations", []),
        "catalog": catalog.model_dump(),
    }


def evaluate(ctx: Context, artifact: dict):
    origins = _fact_origins(ctx)
    refuted = [
        FeedbackItem(severity="major", target=origins.get(s["fact_id"], ""), refs=[s["fact_id"]],
                     problem=f"Утверждение опровергнуто: {s.get('note') or s['fact_id']}",
                     suggestion="Перепроверьте утверждение и замените его подтверждённым")
        for s in artifact.get("statuses", []) if s.get("status") == "refuted"
    ]

    def resolve(item: FeedbackItem):
        for ref in item.refs:
            if ref in origins:
                return origins[ref]
        return None

    return evaluate_verdict(ctx, artifact, extra=refuted, resolve=resolve)


def example(ctx: Context) -> dict:
    return {
        "verdict": "pass",
        "summary": "Ключевые утверждения подтверждены первоисточниками",
        "findings": [],
        "statuses": [{"fact_id": fid, "status": "confirmed", "confidence": 0.9} for fid in _fact_origins(ctx)],
    }


ELEMENT = Element(
    id="factcheck", num="2.5", gate="G0", title="Верификация фактов", actor="Агент-фактчекер", kind="agent",
    checkpoint=True, capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Ошибочный «факт» о конкуренте, отрасли или норме права превращается в ложный дифференциатор или "
            "неверное требование — и дальше уже ни одна проверка его не поймает. Этот фильтр пропускает в синтез "
            "только подтверждённые данные."
        ),
        methods=(
            "Проверка каждого утверждения по первоисточнику — с цитатой и ссылкой",
            "Дата актуальности: устаревшие данные помечаются и перепроверяются",
            "Спорные факты подтверждаются вторым независимым источником",
            "Поиск противоречий между выводами разных агентов фазы 2",
        ),
        prompt=(
            "Для каждого утверждения найди первоисточник и процитируй его. "
            "Нет подтверждения — помечай утверждение как гипотезу, а не факт."
        ),
        done=(
            "Все ключевые утверждения подтверждены первоисточниками или явно помечены как гипотезы; "
            "неподтверждённое отправлено на доисследование."
        ),
        hitl="Эксперт предметной области выборочно проверяет критичные факты.",
        auto_note=(
            "Вместо выборочной проверки экспертом — двойная независимая проверка: спорный факт принимается, "
            "только если его подтверждают второй источник и вторая модель."
        ),
    ),
    consumes=(
        Consumes("competitors", CompetitorAnalysis),
        Consumes("voc", VoiceOfCustomer),
        Consumes("domain", DomainAnalysis),
        Consumes("compliance", ComplianceRegistry),
    ),
    loops=(
        Loop("competitors", "Не подтверждено"),
        Loop("voc", "Не подтверждено", in_reference=False),
        Loop("domain", "Не подтверждено", in_reference=False),
        Loop("compliance", "Не подтверждено", in_reference=False),
    ),
    output=VerifiedResearch,
    agent_output=FactCheckResult,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
