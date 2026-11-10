"""6.4 · Согласование и baseline.

Агент готовит сводку; утверждение — решение на контрольной точке
(человек или агент-арбитр в автономном режиме). После утверждения
требования получают статус approved, baseline замораживается.
"""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.agreement.contracts import Baseline, DebateProtocol, SignoffDraft
from reqpipe.domains.formalization.contracts import SpecBundle


def conditions(spec: SpecBundle) -> dict[str, bool]:
    gates = {g.gate: g.verdict for g in spec.gate_log if g.gate}
    return {
        "все фильтры G1–G6 пройдены": all(gates.get(g) == "pass" for g in ("G1", "G2", "G3", "G4", "G5", "G6")),
        "нет рисков с высоким влиянием без меры": not any(r.impact == "high" and not r.mitigation for r in spec.risks),
        "у каждого требования есть приоритет": all(fr.priority for fr in spec.requirements),
        "у каждого требования есть критерий приёмки": not [g for g in spec.coverage_gaps()
                                                          if g.kind == "fr-without-scenario"],
    }


def finalize(ctx: Context, data: dict) -> dict:
    spec = SpecBundle.model_validate(ctx.input("debate").get("spec", {}))
    return {**data, "conditions": conditions(spec), "approved": False, "spec": spec.model_dump()}


def on_approve(artifact: dict, decision: dict) -> dict:
    spec = SpecBundle.model_validate(artifact.get("spec", {}))
    for fr in spec.requirements:
        fr.status = "approved"
    return {**artifact, "approved": True, "approved_by": decision.get("by", "human"),
            "approved_at": decision.get("at", ""), "low_confidence_decisions": decision.get("low_confidence", []),
            "spec": spec.model_dump()}


def example(ctx: Context) -> dict:
    spec = SpecBundle.model_validate(ctx.input("debate").get("spec", {}))
    return {"executive_summary": f"Спецификация из {len(spec.requirements)} требований готова к утверждению",
            "changes": ["Первая версия"], "disputed_points": [], "risks_summary": f"Рисков: {len(spec.risks)}"}


ELEMENT = Element(
    id="signoff", num="6.4", title="Согласование и baseline", actor="Владелец продукта и эксперты", kind="human",
    checkpoint=True,
    instructions=Instructions(
        purpose=(
            "Человек принимает окончательное решение и несёт за него ответственность. ИИ подготовил всё, чтобы "
            "решение было быстрым и обоснованным."
        ),
        methods=(
            "Сводка для руководителя, подготовленная агентом",
            "Ревью только изменений и спорных мест",
            "Версионирование и управление изменениями",
            "Согласование с фиксацией участников и даты",
        ),
        done=(
            "Спецификация утверждена всеми ответственными, baseline заморожен; дальнейшие изменения — только через "
            "управление изменениями."
        ),
        hitl="Ключевое решение принимают люди.",
        auto_note=(
            "Baseline утверждается автоматически при формальных условиях: пройдены все фильтры G0–G6, критичных "
            "рисков нет, бюджет не превышен. Иначе — повторная итерация, а когда бюджет итераций исчерпан, — "
            "остановка с отчётом."
        ),
    ),
    consumes=(Consumes("debate", DebateProtocol, ("spec", "conflicts", "decisions", "escalations")),),
    output=Baseline,
    agent_output=SignoffDraft,
    finalize=finalize,
    on_approve=on_approve,
    example=example,
)
