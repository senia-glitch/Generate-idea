"""2.1 · Конкурентная разведка."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.clarification.contracts import ProblemStatement
from reqpipe.domains.research.contracts import CompetitorAnalysis


def example(ctx: Context) -> dict:
    src = {"title": "Сайт продукта", "url": "https://example.com/pricing", "quote": "Тариф Pro — 990 ₽/мес",
           "accessed": "2026-11-01"}
    return {
        "competitors": [
            {"id": "CMP-001", "name": "Конкурент А", "kind": "direct", "url": "https://example.com",
             "pricing": "990 ₽/мес", "strengths": ["Известный бренд"], "weaknesses": ["Сложный интерфейс"]},
            {"id": "CMP-002", "name": "Таблицы", "kind": "workaround", "pricing": "бесплатно",
             "strengths": ["Гибкость"], "weaknesses": ["Всё вручную"]},
        ],
        "feature_matrix": [
            {"id": "FEAT-001", "name": "Импорт данных", "user_value": "Не вводить вручную",
             "coverage": {"CMP-001": "good", "CMP-002": "basic"}},
            {"id": "FEAT-002", "name": "Автоматические подсказки", "user_value": "Меньше ошибок",
             "coverage": {"CMP-001": "basic", "CMP-002": "none"}},
            {"id": "FEAT-003", "name": "Совместная работа", "user_value": "Работа в команде",
             "coverage": {"CMP-001": "good", "CMP-002": "good"}},
        ],
        "facts": [{"id": "FCT-CMP-001", "claim": "У конкурента А тариф Pro стоит 990 ₽/мес", "sources": [src]}],
    }


ELEMENT = Element(
    id="competitors", num="2.1", title="Конкурентная разведка", actor="Агент-исследователь рынка", kind="agent",
    capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Построить объективную карту того, что уже умеет рынок. Она нужна для двух целей: паритета — "
            "не уступить в базовых функциях — и превосходства — найти, где обойти."
        ),
        methods=(
            "Веб-поиск, разбор сайтов, документации, changelog и демо",
            "Матрица «функция × конкурент» с оценкой глубины реализации",
            "Анализ тарифов и моделей монетизации",
            "Косвенные конкуренты и обходные решения: таблицы, блокноты, ручной труд",
        ),
        prompt=(
            "Для каждого конкурента опиши функции через пользовательскую ценность, а не маркетинговые слова. "
            "Указывай источник каждого факта."
        ),
        done="Покрыты лидеры рынка и несколько нишевых игроков; у каждого факта есть ссылка на источник.",
    ),
    consumes=(Consumes("frame", ProblemStatement),),
    output=CompetitorAnalysis,
    example=example,
)
