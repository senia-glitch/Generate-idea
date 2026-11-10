"""2.2 · Голос пользователя."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.clarification.contracts import ProblemStatement
from reqpipe.domains.research.contracts import VoiceOfCustomer


def example(ctx: Context) -> dict:
    review = {"title": "Отзыв в магазине приложений", "url": "https://example.com/reviews/1",
              "quote": "Каждый раз ввожу всё заново", "accessed": "2026-11-01"}
    return {
        "pains": [
            {"id": "PAIN-001", "title": "Ручной ввод данных", "situation": "Каждую неделю переносит данные вручную",
             "frequency": 5, "severity": 5, "segments": ["Частные пользователи"], "evidence": [review]},
            {"id": "PAIN-002", "title": "Ошибки в итогах", "situation": "Итоговые суммы не сходятся",
             "frequency": 3, "severity": 4, "segments": ["Малые команды"], "evidence": [review]},
            {"id": "PAIN-003", "title": "Неудобный экспорт", "situation": "Не может выгрузить отчёт",
             "frequency": 2, "severity": 2, "segments": ["Малые команды"], "evidence": [review]},
        ],
        "jobs": [
            {"id": "JTBD-001", "when": "Когда приходят новые данные", "want": "получить их без ручного ввода",
             "so_that": "сэкономить время", "pain_ids": ["PAIN-001"]},
            {"id": "JTBD-002", "when": "Когда готовлю отчёт", "want": "быть уверенным в цифрах",
             "so_that": "не краснеть перед командой", "pain_ids": ["PAIN-002"]},
        ],
        "feature_requests": ["Автоматический импорт", "Проверка итогов"],
        "facts": [{"id": "FCT-VOC-001", "claim": "Пользователи массово жалуются на ручной ввод данных",
                   "sources": [review]}],
    }


ELEMENT = Element(
    id="voc", num="2.2", title="Голос пользователя", actor="Агент анализа отзывов (VoC)", kind="agent",
    capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Узнать, чего пользователям не хватает в существующих решениях. Именно здесь лежит главный "
            "источник будущего превосходства."
        ),
        methods=(
            "Сбор отзывов из магазинов приложений, форумов, соцсетей и сайтов-агрегаторов",
            "Тематическая кластеризация и анализ тональности",
            "Формулировка задач в формате JTBD: «Когда… я хочу… чтобы…»",
            "Оценка частоты и остроты каждой боли",
        ),
        prompt=(
            "Извлекай из отзывов не мнения, а конкретные ситуации, где продукт подвёл пользователя. "
            "Группируй по задаче пользователя, а не по функции."
        ),
        done="Каждая боль подтверждена несколькими независимыми источниками и имеет оценку частоты и остроты.",
    ),
    consumes=(Consumes("frame", ProblemStatement),),
    output=VoiceOfCustomer,
    example=example,
)
