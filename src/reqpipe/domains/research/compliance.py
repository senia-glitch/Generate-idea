"""2.4 · Регуляторика и ограничения."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.clarification.contracts import ProblemStatement
from reqpipe.domains.research.contracts import ComplianceRegistry


def example(ctx: Context) -> dict:
    law = {"title": "Федеральный закон № 152-ФЗ «О персональных данных»", "url": "https://example.com/152fz",
           "quote": "Оператор обязан обеспечить локализацию…", "accessed": "2026-11-01"}
    return {
        "obligations": [
            {"id": "OBL-001", "norm": "152-ФЗ", "jurisdiction": "РФ",
             "requirement": "Система должна хранить персональные данные граждан РФ на серверах в РФ", "source": law},
        ],
        "facts": [{"id": "FCT-LAW-001", "claim": "152-ФЗ требует локализации персональных данных", "sources": [law]}],
    }


ELEMENT = Element(
    id="compliance", num="2.4", title="Регуляторика и ограничения", actor="Агент-комплаенс", kind="agent",
    capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Сразу определить требования, которые нельзя нарушить ни при каком приоритете, — чтобы система "
            "была юридически допустимой на целевых рынках."
        ),
        methods=(
            "Поиск применимых норм: персональные данные (152-ФЗ, GDPR), платежи, отраслевые регламенты",
            "Стандарты доступности (WCAG) и информационной безопасности",
            "Перевод норм права в проверяемые обязательства системы",
        ),
        prompt="Для каждой нормы укажи источник, юрисдикцию и что конкретно система обязана делать или не делать.",
        done="Каждое обязательство привязано к источнику права и юрисдикции.",
    ),
    consumes=(Consumes("frame", ProblemStatement),),
    output=ComplianceRegistry,
    example=example,
)
