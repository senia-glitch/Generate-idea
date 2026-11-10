"""Граф трассируемости: идея → боль → возможность → история → требование → тест."""

from __future__ import annotations

from reqpipe.core import Element, Instructions, TraceCatalog
from reqpipe.domains.platform.contracts import TraceEdge, TraceGraph, TraceNode


def build_graph(artifacts: dict[str, dict]) -> TraceGraph:
    """Собрать граф по всем каталогам и пакетам спецификации, найденным в артефактах."""
    catalog = TraceCatalog()
    requirements: dict[str, dict] = {}
    scenarios: dict[str, dict] = {}
    tests: dict[str, dict] = {}
    for data in artifacts.values():
        if not isinstance(data, dict):
            continue
        catalog.merge(data.get("catalog"))
        spec = data.get("spec") or {}
        catalog.merge(spec.get("catalog"))
        for fr in spec.get("requirements", []) + data.get("requirements", []):
            requirements[fr["id"]] = fr
        for sc in spec.get("scenarios", []):
            scenarios[sc["id"]] = sc
        for t in spec.get("tests", []):
            tests[t["id"]] = t

    nodes = [TraceNode(id=i.id, kind=kind, title=i.title) for kind, items in catalog.items.items() for i in items]
    edges = [TraceEdge(source=i.id, target=ref) for items in catalog.items.values() for i in items for ref in i.refs if ref]
    for fr in requirements.values():
        nodes.append(TraceNode(id=fr["id"], kind="requirement", title=fr.get("title", "")))
        for ref in fr.get("source_ids", []) + fr.get("entity_ids", []) + fr.get("rule_ids", []):
            edges.append(TraceEdge(source=fr["id"], target=ref, kind="derived_from"))
    for sc in scenarios.values():
        nodes.append(TraceNode(id=sc["id"], kind="scenario", title=sc.get("title", "")))
        edges.append(TraceEdge(source=sc["id"], target=sc["requirement_id"], kind="verifies"))
    for t in tests.values():
        nodes.append(TraceNode(id=t["id"], kind="test", title=t.get("file", "")))
        edges.append(TraceEdge(source=t["id"], target=t["scenario_id"], kind="automates"))
    unique = {(n.id, n.kind): n for n in nodes}
    return TraceGraph(nodes=list(unique.values()), edges=edges)


ELEMENT = Element(
    id="trace", num="", title="Граф трассируемости", actor="Сервис связей между артефактами", kind="infra",
    mode="service",
    instructions=Instructions(
        purpose="Позволяет в любой момент ответить на вопросы «зачем нужно это требование?» и «что затронет это изменение?».",
        methods=(
            "Типизированные связи между артефактами всех фаз",
            "Анализ влияния (impact analysis) при изменениях",
            "Поиск «сиротских» элементов без связей",
            "Источник данных для анализа полноты (G3)",
        ),
        done="Каждое требование связано вверх — с болью или обязательством — и вниз — с критерием приёмки.",
    ),
)
