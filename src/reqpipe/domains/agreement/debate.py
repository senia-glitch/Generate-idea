"""6.3 · Дебаты стейкхолдеров. Конфликт с замыслом возвращает конвейер к брифу (1.1)."""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, GateOutcome, Instructions, Loop
from reqpipe.core.gates import route
from reqpipe.domains.agreement.contracts import DebateDraft, DebateProtocol, PrioritizedBacklog
from reqpipe.domains.formalization.contracts import SpecBundle


def finalize(ctx: Context, data: dict) -> dict:
    spec = SpecBundle.model_validate(ctx.input("prioritize").get("spec", {}))
    known = {d.id for d in spec.decisions}
    merged = {**spec.model_dump(),
              "decisions": [d.model_dump() for d in spec.decisions]
              + [d for d in data.get("decisions", []) if d.get("id") not in known]}
    return {**data, "spec": SpecBundle.model_validate(merged).model_dump()}


def evaluate(ctx: Context, artifact: dict) -> GateOutcome:
    revision = artifact.get("scope_revision") or {}
    if not revision.get("needed"):
        return GateOutcome(passed=True)
    item = FeedbackItem(severity="major", target="clarify",
                        problem=f"Пересмотр замысла и scope: {revision.get('reason', '')}")
    return GateOutcome(passed=False, feedback=route(ctx.element, [item]), summary="Нужен пересмотр scope")


def example(ctx: Context) -> dict:
    spec = SpecBundle.model_validate(ctx.input("prioritize").get("spec", {}))
    first = spec.requirements[0].id if spec.requirements else ""
    return {
        "conflicts": [{"id": "CNF-001", "topic": "Объём MVP",
                       "positions": [{"role": "бизнес", "stance": "больше функций в MVP"},
                                     {"role": "архитектор", "stance": "меньше интеграций в первом релизе"}],
                       "resolution": "Одна интеграция в MVP, остальные — в R2", "resolved_by": "consensus",
                       "requirement_ids": [first] if first else []}],
        "decisions": [{"id": "DEC-001", "decision": "В MVP одна интеграция импорта", "rationale": "Снижение риска",
                       "requirement_ids": [first] if first else [], "by": "совет ролей"}],
        "escalations": [],
        "scope_revision": {"needed": False, "reason": ""},
    }


ELEMENT = Element(
    id="debate", num="6.3", title="Дебаты стейкхолдеров", actor="Мультиагентный совет ролей", kind="multi",
    checkpoint=True,
    instructions=Instructions(
        purpose=(
            "Заранее разыграть конфликты интересов, которые иначе всплывут на поздних стадиях, и прийти к "
            "согласованной позиции."
        ),
        methods=(
            "Структурированные дебаты под управлением агента-модератора",
            "Каждый агент защищает свою роль: выручку, удобство, реализуемость, безопасность, законность",
            "Поиск компромиссов и голосование",
            "Эскалация неразрешённых конфликтов человеку",
        ),
        prompt=(
            "Модератор: зафиксируй позиции, найди общие интересы, предложи компромисс. "
            "Если консенсус невозможен — сформулируй вопрос для человека."
        ),
        done="Все конфликты разрешены или эскалированы; каждое решение записано с обоснованием.",
        hitl="Неразрешённые конфликты решает владелец продукта.",
        auto_note=(
            "Неразрешённые конфликты решает агент-арбитр по заранее заданным весам критериев (ценность, риск, "
            "стоимость, законность); каждое такое решение помечается в журнале."
        ),
        auto_prompt=(
            "Модератор: зафиксируй позиции, найди общие интересы, предложи компромисс. Если консенсус невозможен — "
            "передай вопрос агенту-арбитру с позициями сторон и данными."
        ),
    ),
    consumes=(Consumes("prioritize", PrioritizedBacklog, ("spec", "items", "mvp_rationale")),),
    loops=(Loop("clarify", "Пересмотр замысла и scope"),),
    output=DebateProtocol,
    agent_output=DebateDraft,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
