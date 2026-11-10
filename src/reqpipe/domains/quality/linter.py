"""5.1 · G1 Линтер качества требований (ISO/IEC/IEEE 29148).

Детерминированные правила срабатывают ещё до модели: их результаты
включаются в задачу агента и сами по себе могут провалить фильтр.
"""

import re

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.formalization.contracts import AutoTestSuite
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import QualityDraft, QualityReport

FORBIDDEN = (
    "быстро", "удобно", "и т. д", "и т.д", "при необходимости", "интуитивн", "легко", "оптимальн",
    "как можно", "гибко", "эффективн", "примерно", "по возможности", "современн", "user-friendly",
)
SHALL = re.compile(r"\bдолжн[аоы]?\b", re.IGNORECASE)


def check(requirements: list[dict]) -> list[dict]:
    """Правила: запрещённые слова, наличие «должна», атомарность, источник."""
    violations = []
    for fr in requirements:
        text = fr.get("statement", "")
        low = text.lower()
        for word in FORBIDDEN:
            if word in low:
                violations.append({"requirement_id": fr["id"], "rule": "размытая формулировка", "fragment": word})
        shall = len(SHALL.findall(text))
        if shall == 0:
            violations.append({"requirement_id": fr["id"], "rule": "нет обязующего «должна» (EARS)", "fragment": text[:80]})
        elif shall > 1:
            violations.append({"requirement_id": fr["id"], "rule": "не атомарно: несколько «должна»", "fragment": text[:80]})
        if not fr.get("source_ids"):
            violations.append({"requirement_id": fr["id"], "rule": "нет источника требования", "fragment": ""})
    return violations


def prepare(ctx: Context) -> dict:
    return {"rule_violations": check([r.model_dump() for r in spec_of(ctx, "testgen").requirements])}


def finalize(ctx: Context, data: dict) -> dict:
    violations = check([r.model_dump() for r in spec_of(ctx, "testgen").requirements])
    return pass_spec(ctx, "testgen", {**data, "rule_violations": violations})


def evaluate(ctx: Context, artifact: dict):
    extra = [FeedbackItem(severity="major", target="reqwriter", refs=[v["requirement_id"]],
                          problem=f"{v['rule']}: {v['fragment']}".rstrip(": "),
                          suggestion="Переформулируйте требование по шаблону EARS")
             for v in artifact.get("rule_violations", [])]
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    reqs = spec_of(ctx, "testgen").requirements
    return {"verdict": "pass", "summary": "Все требования атомарны, однозначны и проверяемы",
            "findings": [], "scores": [{"requirement_id": r.id} for r in reqs]}


ELEMENT = Element(
    id="quality", num="5.1", gate="G1", title="Линтер качества требований", actor="Скилл по ISO/IEC/IEEE 29148",
    kind="skill",
    instructions=Instructions(
        purpose=(
            "Первый и самый дешёвый фильтр: отсеять плохо сформулированные требования до того, как ими займутся "
            "более дорогие проверки."
        ),
        methods=(
            "Критерии ISO/IEC/IEEE 29148: необходимость, однозначность, атомарность, проверяемость, осуществимость",
            "Словарь запрещённых слов и конструкций",
            "Сверка терминов с глоссарием",
            "Оценка от 0 до 100 и предложение исправления",
        ),
        prompt=(
            "Оцени требование по каждому критерию отдельно. "
            "Если критерий нарушен — предложи исправленную формулировку."
        ),
        done="Все требования набрали пороговую оценку; дефектные возвращены на этап 4.3.",
    ),
    consumes=(Consumes("testgen", AutoTestSuite, ("spec",)),),
    loops=(Loop("reqwriter", "Дефекты формулировок"),),
    output=QualityReport,
    agent_output=QualityDraft,
    prepare=prepare,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
