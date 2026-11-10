"""Общая логика фильтров качества: вердикт и маршрутизация замечаний по петлям."""

from __future__ import annotations

from typing import Callable, Iterable

from reqpipe.core.contracts import FeedbackItem
from reqpipe.core.element import Context, Element, GateOutcome


def route(
    element: Element,
    findings: Iterable[FeedbackItem | dict],
    resolve: Callable[[FeedbackItem], str | None] | None = None,
) -> dict[str, list[FeedbackItem]]:
    """Разложить замечания по адресатам петель элемента.

    Адресат берётся из ``item.target``, затем из ``resolve(item)``, иначе —
    петля по умолчанию (первая объявленная).
    """
    allowed = set(element.loop_targets)
    routed: dict[str, list[FeedbackItem]] = {}
    for n, raw in enumerate(findings, 1):
        item = raw if isinstance(raw, FeedbackItem) else FeedbackItem.model_validate(raw)
        if not item.id:
            item.id = f"{element.id.upper()}-{n:03d}"
        target = item.target if item.target in allowed else None
        if target is None and resolve is not None:
            candidate = resolve(item)
            target = candidate if candidate in allowed else None
        target = target or element.default_loop_target()
        if target:
            item.target = target
            routed.setdefault(target, []).append(item)
    return routed


def evaluate_verdict(ctx: Context, artifact: dict, extra: Iterable[FeedbackItem] = (), resolve=None) -> GateOutcome:
    """Стандартное решение фильтра: провал, если агент сказал «fail» или есть детерминированные замечания."""
    extra = list(extra)
    findings = list(artifact.get("findings", [])) + extra
    failed = artifact.get("verdict") == "fail" or any(
        (f.severity if isinstance(f, FeedbackItem) else f.get("severity", "major")) in ("critical", "major")
        for f in extra
    )
    if not failed:
        return GateOutcome(passed=True, summary=artifact.get("summary", ""))
    blocking = [f for f in findings
                if (f.severity if isinstance(f, FeedbackItem) else f.get("severity", "major")) != "minor"] or findings
    if not blocking:
        blocking = [FeedbackItem(problem=artifact.get("summary") or "Фильтр не пройден", severity="major")]
    return GateOutcome(passed=False, feedback=route(ctx.element, blocking, resolve), summary=artifact.get("summary", ""))
