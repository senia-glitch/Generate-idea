"""6.1 · Оценка реализуемости. Невыполнимое уходит на переписывание в 4.3."""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.agreement.contracts import FeasibilityDraft, FeasibilityReport
from reqpipe.domains.formalization.contracts import SpecBundle
from reqpipe.domains.quality.contracts import BenchmarkScorecard


def _spec(ctx: Context) -> SpecBundle:
    return SpecBundle.model_validate(ctx.input("benchmark").get("spec", {}))


def finalize(ctx: Context, data: dict) -> dict:
    spec = _spec(ctx)
    items = {i["requirement_id"]: i for i in data.get("items", [])}
    for fr in spec.requirements:
        if fr.id in items:
            fr.feasible = items[fr.id].get("feasible", True)
            fr.size = items[fr.id].get("size", "M")
    known = {r.id for r in spec.risks}
    spec.risks += [r for r in (FeasibilityReport.model_validate({"verdict": "pass", **data}).risks) if r.id not in known]
    spec.architecture = data.get("architecture", {})
    spec.log_gate("", ctx.element.id, data.get("verdict", ""), data.get("summary", ""))
    return {**data, "spec": spec.model_dump()}


def evaluate(ctx: Context, artifact: dict):
    extra = [FeedbackItem(severity="major", target="reqwriter", refs=[i["requirement_id"]],
                          problem=f"Требование {i['requirement_id']} невыполнимо: {i.get('risk', '')}",
                          suggestion=i.get("alternative", ""))
             for i in artifact.get("items", []) if not i.get("feasible", True)]
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    sizes = ["S", "M", "L", "M"]
    return {
        "verdict": "pass", "summary": "Все требования реализуемы известными средствами", "findings": [],
        "architecture": {"components": ["Веб-клиент", "API", "Сервис импорта"], "integrations": ["Банковские выписки"],
                         "data_stores": ["PostgreSQL (РФ)"]},
        "items": [{"requirement_id": r.id, "feasible": True, "size": sizes[n % len(sizes)], "risk": "низкий"}
                  for n, r in enumerate(_spec(ctx).requirements)],
        "risks": [{"id": "RSK-002", "description": "Нестабильные форматы выписок", "impact": "medium",
                   "mitigation": "Адаптеры на каждый формат", "source": "feasibility"}],
    }


ELEMENT = Element(
    id="feasibility", num="6.1", title="Оценка реализуемости", actor="Агент-архитектор", kind="agent",
    checkpoint=True, capabilities=frozenset({"code"}),
    instructions=Instructions(
        purpose=(
            "Требования должны позволять построить систему: невыполнимое или непомерно дорогое требование "
            "обесценивает спецификацию. Кроме того, без оценки трудоёмкости невозможна честная приоритизация."
        ),
        methods=(
            "Архитектурный эскиз: основные компоненты, интеграции, данные",
            "Проверка осуществимости каждого требования (критерий «feasible» ISO/IEC/IEEE 29148)",
            "Грубая оценка трудоёмкости в относительных единицах (T-shirt sizing)",
            "Технические прототипы (spike) для требований с высокой неопределённостью",
        ),
        prompt=(
            "Для каждого требования ответь: реализуемо ли оно известными средствами, во что обойдётся и в чём "
            "главный технический риск. Невыполнимое помечай и предлагай реализуемую альтернативу."
        ),
        done=(
            "У каждого требования есть признак осуществимости и оценка трудоёмкости; невыполнимые заменены или "
            "исключены с обоснованием."
        ),
        hitl="Ведущий разработчик подтверждает оценки и риски.",
        auto_note=(
            "Оценки принимаются без подтверждения разработчиком; для требований с высокой неопределённостью "
            "берётся пессимистичная оценка."
        ),
    ),
    consumes=(Consumes("benchmark", BenchmarkScorecard, ("spec",)),),
    loops=(Loop("reqwriter", "Невыполнимо → переписать требование"),),
    output=FeasibilityReport,
    agent_output=FeasibilityDraft,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
