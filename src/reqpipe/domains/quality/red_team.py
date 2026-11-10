"""5.2 · G2 Красная команда."""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import CriticDraft, CriticReport, QualityReport


def finalize(ctx: Context, data: dict) -> dict:
    spec = spec_of(ctx, "quality")
    known = {r.id for r in spec.risks}
    risks = [r.model_dump() for r in spec.risks] + [r for r in data.get("risks", []) if r.get("id") not in known]
    return pass_spec(ctx, "quality", data, risks=risks)


def evaluate(ctx: Context, artifact: dict):
    extra = [FeedbackItem(severity="major", target="reqwriter", refs=c["requirement_ids"],
                          problem=f"Противоречие: {c['explanation']}")
             for c in artifact.get("contradictions", [])]
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    reqs = spec_of(ctx, "quality").requirements
    return {
        "verdict": "pass", "summary": "Критичных противоречий не найдено",
        "findings": [], "contradictions": [],
        "abuse_cases": ["Массовый импорт поддельных данных для перегрузки системы"],
        "risks": [{"id": "RSK-001", "description": "Источник данных меняет формат без предупреждения",
                   "impact": "medium", "mitigation": "Версионирование импорта и мониторинг ошибок",
                   "source": reqs[0].id if reqs else ""}],
    }


ELEMENT = Element(
    id="critic", num="5.2", gate="G2", title="Красная команда", actor="Агент-критик", kind="agent",
    instructions=Instructions(
        purpose="Состязательная проверка: независимый агент целенаправленно пытается «сломать» спецификацию.",
        methods=(
            "Поиск пар противоречащих требований",
            "Глобальная проверка непротиворечивости всего набора: требования разных эпиков сверяются через общие "
            "сущности, состояния и бизнес-правила модели данных",
            "Сценарии злоупотреблений (abuse cases)",
            "Анализ «а что, если…» для сбоев, гонок и потери данных",
            "Отдельная модель или промпт, не участвовавшие в написании требований",
        ),
        prompt=(
            "Ты — скептичный эксперт, который ищет причины, почему продукт провалится. "
            "Найди не меньше десяти проблем и ранжируй их по ущербу."
        ),
        done="Все критические дефекты закрыты или осознанно приняты с обоснованием.",
    ),
    consumes=(Consumes("quality", QualityReport, ("spec",)),),
    loops=(Loop("reqwriter", "Критические дефекты", in_reference=False),),
    output=CriticReport,
    agent_output=CriticDraft,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
