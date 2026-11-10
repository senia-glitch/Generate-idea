"""3.3 · Персоны и сценарии."""

from reqpipe.core import CatalogItem, Consumes, Context, Element, Instructions, TraceCatalog
from reqpipe.domains.research.contracts import VerifiedResearch
from reqpipe.domains.strategy.contracts import PersonasAndScenarios, PersonasDraft


def finalize(ctx: Context, data: dict) -> dict:
    research = ctx.input("factcheck")
    catalog = TraceCatalog.combine(research.get("catalog"))
    catalog.add("persona", [CatalogItem(id=p["id"], title=p["name"], refs=p.get("pain_ids", []))
                            for p in data.get("personas", [])])
    catalog.add("scenario", [CatalogItem(id=s["id"], title=s["title"], refs=[s.get("persona_id", "")])
                             for s in data.get("scenarios", [])])
    return {**data, "catalog": catalog.model_dump()}


def example(ctx: Context) -> dict:
    pains = [p["id"] for p in ctx.input("factcheck").get("pains", [])]
    return {
        "personas": [
            {"id": "PER-001", "name": "Анна, частный пользователь", "role": "Пользователь",
             "goals": ["Тратить на учёт меньше 10 минут в неделю"], "pain_ids": pains[:2], "skills": "Базовые"},
            {"id": "PER-002", "name": "Олег, руководитель малой команды", "role": "Администратор",
             "goals": ["Получать точные отчёты"], "pain_ids": pains[1:], "skills": "Уверенные"},
        ],
        "roles": [
            {"id": "ROLE-001", "name": "Пользователь", "permissions": ["создавать записи", "смотреть отчёты"]},
            {"id": "ROLE-002", "name": "Администратор", "permissions": ["управлять командой", "выгружать отчёты"]},
        ],
        "journey": [
            {"id": "CJS-001", "stage": "Получение данных", "action": "Загружает выписку", "emotion": "раздражение",
             "pain_ids": pains[:1]},
            {"id": "CJS-002", "stage": "Отчёт", "action": "Проверяет итоги", "emotion": "тревога",
             "pain_ids": pains[1:2]},
        ],
        "scenarios": [
            {"id": "SCN-001", "title": "Импорт данных без ручного ввода", "persona_id": "PER-001", "kind": "main",
             "steps": ["Подключить источник", "Подтвердить импорт", "Проверить категории"]},
            {"id": "SCN-002", "title": "Формирование точного отчёта", "persona_id": "PER-002", "kind": "main",
             "steps": ["Выбрать период", "Сформировать отчёт", "Выгрузить"]},
        ],
    }


ELEMENT = Element(
    id="personas", num="3.3", title="Персоны и сценарии", actor="Агент UX-исследователь", kind="agent",
    instructions=Instructions(
        purpose=(
            "Описать, кто и как будет пользоваться системой, чтобы требования выводились из реальных "
            "сценариев, а не из списка функций."
        ),
        methods=(
            "Персоны на основе данных VoC, а не фантазии",
            "Модель ролей и прав доступа",
            "Customer Journey Map с эмоциями и точками боли",
            "Основные, альтернативные и исключительные сценарии",
        ),
        prompt=(
            "Каждая персона должна опираться на кластеры из анализа отзывов. "
            "Для каждого этапа пути укажи боль и возможность."
        ),
        done="Каждая роль системы имеет персону и хотя бы один сквозной сценарий.",
    ),
    consumes=(Consumes("factcheck", VerifiedResearch, ("pains", "jobs", "catalog"), note="боли и Jobs-to-be-Done"),),
    output=PersonasAndScenarios,
    agent_output=PersonasDraft,
    finalize=finalize,
    example=example,
)
