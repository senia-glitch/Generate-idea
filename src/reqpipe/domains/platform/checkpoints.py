"""Контрольные точки: решение человека или — в автономном режиме — агента-арбитра.

Арбитр по умолчанию работает по правилам (``arbiter = "rules"``): одобряет
результат, прошедший контракт и фильтры, и оценивает уверенность по числу
допущений, гипотез и эскалаций. Решения с уверенностью ниже порога
попадают в список «для просмотра людьми». Режим ``arbiter = "executor"``
отдаёт решение агенту (см. оркестратор).
"""

from __future__ import annotations

import json
from typing import Any

from reqpipe.core import Element, Instructions
from reqpipe.core.config import RunConfig
from reqpipe.domains.platform.contracts import CheckpointDecision
from reqpipe.domains.platform.knowledge_base import Workspace, now


def summarize(data: dict[str, Any], limit: int = 3) -> str:
    """Короткая сводка артефакта для человека: поля, размеры списков, первые элементы."""
    lines = []
    for key, value in data.items():
        if key in ("spec", "catalog"):
            if isinstance(value, dict) and key == "spec":
                lines.append(f"• spec: требований {len(value.get('requirements', []))}, "
                             f"сценариев {len(value.get('scenarios', []))}, тестов {len(value.get('tests', []))}")
            continue
        if isinstance(value, list):
            preview = []
            for item in value[:limit]:
                if isinstance(item, dict):
                    title = item.get("title") or item.get("name") or item.get("statement") or item.get("claim") \
                        or item.get("problem") or item.get("decision") or item.get("question") or item.get("id") or ""
                    preview.append(f"{item.get('id', '')} {title}".strip()[:110])
                else:
                    preview.append(str(item)[:110])
            more = f" … ещё {len(value) - limit}" if len(value) > limit else ""
            lines.append(f"• {key} ({len(value)}): " + "; ".join(preview) + more)
        elif isinstance(value, dict):
            lines.append(f"• {key}: {json.dumps(value, ensure_ascii=False)[:160]}")
        elif value not in ("", None):
            lines.append(f"• {key}: {str(value)[:200]}")
    return "\n".join(lines)


class Checkpoints:
    def __init__(self, workspace: Workspace, config: RunConfig):
        self.ws = workspace
        self.config = config

    def rules_decision(self, element: Element, artifact: dict, kind: str = "approval") -> CheckpointDecision:
        confidence = 0.9
        confidence -= min(0.3, 0.05 * len(artifact.get("hypotheses", [])))
        confidence -= min(0.2, 0.05 * len(artifact.get("assumptions", [])))
        confidence -= min(0.3, 0.1 * len(artifact.get("escalations", [])))
        confidence -= 0.2 * sum(1 for ok in artifact.get("conditions", {}).values() if not ok)
        confidence = round(max(0.0, confidence), 2)
        return CheckpointDecision(
            element_id=element.id, kind=kind, decision="approve", by="arbiter", confidence=confidence,
            low_confidence=confidence < self.config.arbiter_min_confidence,
            comment="Решение по правилам: результат прошёл контракт и фильтры", at=now(),
        )

    def loop_budget_decision(self, element: Element, findings: list[dict]) -> CheckpointDecision:
        critical = [f for f in findings if f.get("severity") == "critical"]
        if critical:
            return CheckpointDecision(element_id=element.id, kind="loop_budget", decision="stop", by="arbiter",
                                      comment=f"Бюджет итераций исчерпан, критичных замечаний: {len(critical)}", at=now())
        return CheckpointDecision(element_id=element.id, kind="loop_budget", decision="approve", by="arbiter",
                                  confidence=0.5, low_confidence=True, at=now(),
                                  comment="Бюджет итераций исчерпан; некритичные замечания приняты как риск")

    def record(self, decision: CheckpointDecision) -> dict:
        data = decision.model_dump()
        self.ws.append_decision(data)
        return data

    @staticmethod
    def arbiter_prompt(element: Element, artifact: dict, autonomous_note: str) -> str:
        return "\n".join([
            f"# Решение агента-арбитра: этап {element.num} «{element.title}»",
            "",
            "Ты — агент-арбитр конвейера требований. Реши, можно ли принять результат этапа и идти дальше.",
            "Принимай решение только на основании данных в артефакте и критерия готовности. Если данных",
            "недостаточно — выбирай вариант с наименьшим риском и объясни почему.",
            "",
            f"## Критерий готовности\n{element.instructions.done}",
            f"## Что важно в автономном режиме\n{autonomous_note or '—'}",
            "## Результат этапа (сводка)",
            summarize(artifact, limit=8),
            "",
            "Верни JSON: {\"decision\": \"approve\" | \"reject\", \"confidence\": 0..1, \"rationale\": \"…\"}",
        ])


ELEMENT = Element(
    id="hitl", num="", title="Контрольные точки человека", actor="Автор идеи, эксперты, владелец продукта",
    kind="human", mode="service",
    instructions=Instructions(
        purpose=(
            "Гарантирует, что процесс остаётся под контролем людей: ИИ ускоряет и расширяет анализ, но не принимает "
            "за людей ключевые решения."
        ),
        methods=(
            "Сводка фазы: что сделано, что спорно, что требует решения",
            "Утверждение или возврат с комментарием",
            "Экспертная проверка фактов предметной области",
            "Фиксация решений в журнале",
        ),
        done="Каждая фаза закрыта явным решением ответственного человека.",
        auto_note=(
            "Агент-арбитр закрывает все контрольные точки по правилам и порогам уверенности, заданным до запуска; "
            "каждое решение с обоснованием попадает в журнал, решения с низкой уверенностью — в отдельный список."
        ),
    ),
)
