"""5.6 · G6 Конкурентный бенчмарк — по критериям, зафиксированным на этапе 3.2."""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import BenchmarkDraft, BenchmarkScorecard, UserTestReport
from reqpipe.domains.strategy.contracts import ProductVision

STRONG = ("good", "excellent")


def _base_features(ctx: Context) -> set[str]:
    """Базовые функции рынка: те, что хотя бы один конкурент реализует хорошо."""
    return {row["id"] for row in ctx.input("vision").get("competitive_baseline", [])
            if any(depth in STRONG for depth in row.get("coverage", {}).values())}


def finalize(ctx: Context, data: dict) -> dict:
    weights = {c["id"]: c.get("weight", 0) for c in ctx.input("vision").get("superiority_criteria", [])}
    ours = sum(weights.get(s["criterion_id"], 0) * s["our_score"] for s in data.get("superiority", []))
    best = sum(weights.get(s["criterion_id"], 0) * s["best_competitor_score"] for s in data.get("superiority", []))
    data = {**data, "weighted_ours": round(ours, 2), "weighted_best_competitor": round(best, 2)}
    summary = {"weighted_ours": data["weighted_ours"], "weighted_best_competitor": data["weighted_best_competitor"],
               "why_switch": data.get("why_switch_answer", "")}
    return pass_spec(ctx, "usertest", data, benchmark=summary)


def evaluate(ctx: Context, artifact: dict):
    extra = []
    criteria = {c["id"] for c in ctx.input("vision").get("superiority_criteria", [])}
    scored = {s["criterion_id"] for s in artifact.get("superiority", [])}
    for missing in sorted(criteria - scored):
        extra.append(FeedbackItem(severity="major", target="gap", refs=[missing],
                                  problem=f"Критерий превосходства {missing} не оценён"))
    if criteria and artifact.get("weighted_ours", 0) <= artifact.get("weighted_best_competitor", 0):
        extra.append(FeedbackItem(severity="major", target="gap",
                                  problem="Нет перевеса над лучшим конкурентом по взвешенной оценке критериев"))
    covered = {p["feature_id"] for p in artifact.get("parity", []) if p.get("status") == "covered"}
    for feature in sorted(_base_features(ctx) - covered):
        extra.append(FeedbackItem(severity="major", target="gap", refs=[feature],
                                  problem=f"Нет паритета по базовой функции рынка {feature}"))
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    vision = ctx.input("vision")
    frs = [r.id for r in spec_of(ctx, "usertest").requirements]
    return {
        "verdict": "pass", "summary": "Паритет по базовым функциям, перевес по каждому критерию", "findings": [],
        "parity": [{"feature_id": row["id"], "status": "covered", "requirement_ids": frs[:1]}
                   for row in vision.get("competitive_baseline", [])],
        "superiority": [{"criterion_id": c["id"], "our_score": 8, "best_competitor_score": 5,
                         "requirement_ids": frs[:2]} for c in vision.get("superiority_criteria", [])],
        "why_switch_answer": vision.get("why_switch", ""),
    }


ELEMENT = Element(
    id="benchmark", num="5.6", gate="G6", title="Конкурентный бенчмарк", actor="Агент-стратег", kind="agent",
    capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Финальный стратегический фильтр: подтвердить, что спецификация описывает систему лучше конкурентов, "
            "а не ещё одну такую же."
        ),
        methods=(
            "Оценка по критериям превосходства, зафиксированным на этапе 3.2, — без их пересмотра задним числом",
            "Паритет: все базовые функции лидеров рынка покрыты",
            "Превосходство: по каждому дифференциатору есть требования, которых нет у конкурентов",
            "Взвешенная оценка по значимым для пользователя критериям",
            "Проверочный вопрос: «Почему пользователь перейдёт к нам?»",
        ),
        prompt=(
            "Для каждого конкурента ответь: что есть у него и нет у нас, и что есть у нас и нет у него. "
            "Если перевеса нет — так и скажи."
        ),
        done="Паритет по базовым функциям — полный, перевес есть по каждому заявленному дифференциатору.",
    ),
    consumes=(
        Consumes("usertest", UserTestReport, ("spec",)),
        Consumes("vision", ProductVision,
                 ("superiority_criteria", "differentiators", "competitive_baseline", "competitors", "why_switch"),
                 note="критерии превосходства"),
    ),
    loops=(Loop("gap", "Нет превосходства"),),
    output=BenchmarkScorecard,
    agent_output=BenchmarkDraft,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
