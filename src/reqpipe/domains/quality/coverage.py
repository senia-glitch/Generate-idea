"""5.3 · G3 Анализ полноты.

Полнота по ID проверяется детерминированно (``SpecBundle.coverage_gaps``),
агент ищет смысловые пробелы: типовые функции домена, недостающие сценарии.
"""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import CoverageDraft, CoverageReport, CriticReport

TRACE_KINDS = ("pain", "obligation", "story", "differentiator", "entity")


def prepare(ctx: Context) -> dict:
    spec = spec_of(ctx, "critic")
    return {"deterministic_gaps": [g.model_dump() for g in spec.coverage_gaps()],
            "orphans": spec.orphan_requirements()}


def finalize(ctx: Context, data: dict) -> dict:
    spec = spec_of(ctx, "critic")
    refs = spec.references()
    matrix = [{"source_id": item.id, "kind": kind, "requirement_ids": sorted(refs.get(item.id, set()))}
              for kind in TRACE_KINDS for item in spec.catalog.get(kind)]
    gaps = [g.model_dump() for g in spec.coverage_gaps()] + list(data.get("semantic_gaps", []))
    data = {k: v for k, v in data.items() if k != "semantic_gaps"}
    return pass_spec(ctx, "critic", {**data, "matrix": matrix, "gaps": gaps, "orphans": spec.orphan_requirements()})


def evaluate(ctx: Context, artifact: dict):
    extra = [FeedbackItem(severity="major", target=g.get("target") or "storymap", refs=[g["id"]],
                          problem=f"Не покрыто требованиями ({g['kind']}): {g.get('title') or g['id']}",
                          suggestion="Добавьте историю или требование, закрывающее этот элемент")
             for g in artifact.get("gaps", [])]
    extra += [FeedbackItem(severity="major", target="reqwriter", refs=[o],
                           problem=f"«Сиротское» требование {o}: источник не найден в каталоге")
              for o in artifact.get("orphans", [])]
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    return {"verdict": "pass", "summary": "Все приоритетные боли и обязательства покрыты", "findings": [],
            "semantic_gaps": []}


ELEMENT = Element(
    id="coverage", num="5.3", gate="G3", title="Анализ полноты", actor="Агент трассировки", kind="agent",
    instructions=Instructions(
        purpose=(
            "Доказать полноту: ни одна потребность, найденная в исследовании, не потерялась на пути к требованиям."
        ),
        methods=(
            "Прямая и обратная трассировка: боль → возможность → история → требование → тест",
            "CRUD-матрица «сущность × операция»",
            "Покрытие всех состояний и переходов",
            "Чек-листы типовых функций домена: поиск, экспорт, уведомления, аудит",
        ),
        prompt=(
            "Найди всё, что ни на что не ссылается и на что никто не ссылается. "
            "Каждый пробел оформи как предложение новой истории."
        ),
        done="Покрыты все приоритетные боли и все обязательства; «сиротских» требований нет.",
    ),
    consumes=(Consumes("critic", CriticReport, ("spec",)),),
    loops=(Loop("storymap", "Пробелы покрытия"), Loop("reqwriter", "Пробелы покрытия", in_reference=False)),
    output=CoverageReport,
    agent_output=CoverageDraft,
    prepare=prepare,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
