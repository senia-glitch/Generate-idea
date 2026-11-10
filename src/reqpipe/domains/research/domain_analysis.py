"""2.3 · Анализ предметной области."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.clarification.contracts import ProblemStatement
from reqpipe.domains.research.contracts import DomainAnalysis


def example(ctx: Context) -> dict:
    src = {"title": "Отраслевой стандарт", "url": "https://example.com/standard", "quote": "Запись — единица учёта",
           "accessed": "2026-11-01"}
    return {
        "glossary": [
            {"term": "Запись", "definition": "Единица учёта, внесённая пользователем", "example": "Покупка на 500 ₽"},
            {"term": "Категория", "definition": "Группа записей одного типа", "example": "Продукты"},
            {"term": "Отчёт", "definition": "Сводка записей за период", "example": "Отчёт за октябрь"},
        ],
        "entities": [
            {"id": "ENT-001", "name": "Запись", "attributes": ["сумма", "дата", "категория"]},
            {"id": "ENT-002", "name": "Отчёт", "attributes": ["период", "итоги"]},
        ],
        "processes": [{"id": "PRC-001", "name": "Учёт записей", "actors": ["Пользователь"],
                       "steps": ["Получить данные", "Разнести по категориям", "Сформировать отчёт"]}],
        "facts": [{"id": "FCT-DOM-001", "claim": "Запись — базовая единица учёта в отрасли", "sources": [src]}],
    }


ELEMENT = Element(
    id="domain", num="2.3", title="Анализ предметной области", actor="Агент-доменный аналитик", kind="agent",
    capabilities=frozenset({"web"}),
    instructions=Instructions(
        purpose=(
            "Дать всем агентам и людям общий язык и модель предметной области, чтобы требования были "
            "корректны с точки зрения отрасли."
        ),
        methods=(
            "RAG по отраслевой литературе, стандартам и экспертным материалам",
            "Извлечение сущностей, атрибутов и связей",
            "Моделирование процессов в нотации BPMN",
            "Единый язык (ubiquitous language) в духе DDD",
        ),
        prompt=(
            "Каждый термин определи однозначно и приведи пример. "
            "Отметь термины, которые в отрасли трактуются по-разному."
        ),
        done="Глоссарий покрывает все термины брифа; ключевые процессы смоделированы и проверены экспертом.",
        auto_note="Вместо проверки экспертом модель процессов сверяется с первоисточниками на этапе G0.",
    ),
    consumes=(Consumes("frame", ProblemStatement),),
    output=DomainAnalysis,
    example=example,
)
