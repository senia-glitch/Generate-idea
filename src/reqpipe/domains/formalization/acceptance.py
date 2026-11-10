"""4.4 · Критерии приёмки."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.formalization.contracts import AcceptanceDraft, AcceptanceSuite, RequirementsRegistry


def finalize(ctx: Context, data: dict) -> dict:
    registry = ctx.input("reqwriter")
    return {**data, "requirements": registry.get("requirements", []), "catalog": registry.get("catalog", {})}


def example(ctx: Context) -> dict:
    scenarios = []
    n = 0
    for fr in ctx.input("reqwriter").get("requirements", []):
        for kind, then in (("positive", "результат сохранён"), ("negative", "показано понятное сообщение об ошибке")):
            n += 1
            scenarios.append({
                "id": f"AC-{n:03d}", "requirement_id": fr["id"], "kind": kind, "title": f"{fr['id']}: {kind}",
                "gherkin": (f"Функция: {fr['title']}\n  Сценарий: {kind}\n    Дано пользователь авторизован\n"
                            f"    Когда он выполняет действие из {fr['id']}\n    Тогда {then}"),
            })
    return {"scenarios": scenarios}


ELEMENT = Element(
    id="acceptance", num="4.4", title="Критерии приёмки", actor="Скилл BDD / Gherkin", kind="skill",
    instructions=Instructions(
        purpose=(
            "Сделать каждое требование проверяемым: если для требования нельзя написать критерий приёмки, "
            "оно сформулировано плохо."
        ),
        methods=(
            "Структура Given / When / Then",
            "Позитивные, негативные и граничные сценарии",
            "Таблицы примеров (Scenario Outline)",
            "Готовность к автоматизации тестов",
        ),
        prompt=(
            "Для каждого требования — минимум один позитивный и один негативный сценарий. "
            "Граничные значения бери из бизнес-правил модели."
        ),
        done="У каждого функционального требования есть исполнимые критерии приёмки.",
    ),
    consumes=(Consumes("reqwriter", RequirementsRegistry),),
    output=AcceptanceSuite,
    agent_output=AcceptanceDraft,
    finalize=finalize,
    example=example,
)
