"""1.2 · Постановка проблемы."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.clarification.contracts import IdeaBrief, ProblemStatement, ProblemStatementDraft


def finalize(ctx: Context, data: dict) -> dict:
    brief = ctx.input("clarify")
    return {
        **data,
        "audience": brief.get("target_audience", []),
        "constraints": brief.get("constraints", []),
        "assumptions": brief.get("assumptions", []),
    }


def example(ctx: Context) -> dict:
    brief = ctx.input("clarify")
    return {
        "statement": brief.get("problem", "Проблема не сформулирована"),
        "who_suffers": ", ".join(brief.get("target_audience", [])) or "Целевая аудитория",
        "context": brief.get("context", ""),
        "cost_of_problem": "Несколько часов в неделю и ошибки в результатах",
        "value_hypothesis": "Автоматизация рутины сократит время вдвое",
        "success_metrics": [{"name": "Время на задачу", "target": "−50%"}],
        "in_scope": ["Основной пользовательский сценарий"],
        "out_of_scope": ["Интеграции с корпоративными системами"],
        "lean_canvas": {"problem": brief.get("problem", ""), "solution": "Сервис-помощник"},
    }


ELEMENT = Element(
    id="frame", num="1.2", title="Постановка проблемы", actor="Скилл Problem Framing", kind="skill",
    instructions=Instructions(
        purpose=(
            "Зафиксировать, что и для кого мы решаем, до начала исследования — чтобы все последующие "
            "агенты работали в одних и тех же рамках."
        ),
        methods=(
            "Шаблон Problem Statement: кто страдает, от чего, в каком контексте и во что это обходится",
            "Lean Canvas как одностраничная модель продукта",
            "Явные списки in-scope и out-of-scope",
            "Измеримые критерии успеха продукта",
        ),
        prompt=(
            "Сформулируй проблему так, чтобы её можно было опровергнуть данными. "
            "Отдели проблему от предлагаемого решения."
        ),
        done="Проблема сформулирована измеримо, границы согласованы с автором идеи.",
        auto_note=(
            "Границы scope не согласуются с автором, а фиксируются как допущения: их подтверждают "
            "или опровергают данные исследования."
        ),
    ),
    consumes=(Consumes("clarify", IdeaBrief),),
    output=ProblemStatement,
    agent_output=ProblemStatementDraft,
    finalize=finalize,
    example=example,
)
