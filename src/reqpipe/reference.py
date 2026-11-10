"""Сверка системы с эталонной схемой ``requirements-pipeline.html``.

Эталон не меняется: его SHA-256 зафиксирован ниже. Сверка проверяет, что
* каждой карточке схемы соответствует элемент с тем же ID, номером, названием и фильтром;
* каждая дорожка схемы — домен, и элемент лежит в домене своей дорожки;
* прямые контракты реестра в точности совпадают со стрелками схемы;
* все петли схемы реализованы (реестр может содержать дополнительные — уточнения).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path

from reqpipe.core import Registry

REFERENCE_FILE = "requirements-pipeline.html"
REFERENCE_SHA256 = "3dab1225f9663abf6b991547a8a1a4b4a451e05954adf547dc722126e888e1b9"

NODE_RE = re.compile(r"\{ id:'(?P<id>[a-z]+)', phase:'(?P<phase>p\w)'(?P<rest>[^\n]*)\n\s*title:'(?P<title>[^']*)'")
NUM_RE = re.compile(r"num:'([^']*)'")
GATE_RE = re.compile(r"gate:'(G\d)'")
KIND_RE = re.compile(r"kind:'(\w+)'")
EDGE_RE = re.compile(r"\['(\w+)','(\w+)'")
LOOP_RE = re.compile(r"from:'(\w+)',\s*to:'(\w+)'")


@dataclass
class ReferenceNode:
    id: str
    phase: str
    num: str
    title: str
    gate: str
    kind: str


@dataclass
class Reference:
    nodes: dict[str, ReferenceNode]
    edges: set[tuple[str, str]]
    loops: set[tuple[str, str]]
    sha256: str


@dataclass
class ConformanceReport:
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def _block(text: str, start: str) -> str:
    i = text.index(start)
    return text[i: text.index("];", i)]


def parse_reference(path: str | Path) -> Reference:
    raw = Path(path).read_bytes()
    text = raw.decode("utf-8")
    nodes_block = _block(text, "const NODES = [")
    nodes = {}
    for m in NODE_RE.finditer(nodes_block):
        rest = m.group("rest")
        num = NUM_RE.search(rest)
        gate = GATE_RE.search(rest)
        kind = KIND_RE.search(rest)
        nodes[m.group("id")] = ReferenceNode(
            id=m.group("id"), phase=m.group("phase"), num=num.group(1) if num else "",
            title=m.group("title"), gate=gate.group(1) if gate else "", kind=kind.group(1) if kind else "",
        )
    edges = set(EDGE_RE.findall(_block(text, "const EDGES = [")))
    loops = set(LOOP_RE.findall(_block(text, "const LOOPS = [")))
    return Reference(nodes=nodes, edges=edges, loops=loops, sha256=hashlib.sha256(raw).hexdigest())


def check(registry: Registry, reference_path: str | Path) -> ConformanceReport:
    report = ConformanceReport()
    ref = parse_reference(reference_path)
    if ref.sha256 != REFERENCE_SHA256:
        report.errors.append(f"Эталон изменён: SHA-256 {ref.sha256[:12]}… ≠ зафиксированного {REFERENCE_SHA256[:12]}…")

    phase_domain = {d.phase: d.id for d in registry.domains.values()}
    for node in ref.nodes.values():
        element = registry.elements.get(node.id)
        if element is None:
            report.errors.append(f"Карточка {node.id} «{node.title}» не реализована")
            continue
        if node.phase not in phase_domain:
            report.errors.append(f"Дорожка {node.phase} не реализована доменом")
        elif element.domain != phase_domain[node.phase]:
            report.errors.append(f"{node.id}: элемент в домене {element.domain}, а на схеме — в {phase_domain[node.phase]}")
        if element.num != node.num:
            report.errors.append(f"{node.id}: номер {element.num!r} ≠ {node.num!r} на схеме")
        if element.title != node.title:
            report.errors.append(f"{node.id}: название «{element.title}» ≠ «{node.title}» на схеме")
        if (element.gate or "") != node.gate:
            report.errors.append(f"{node.id}: фильтр {element.gate!r} ≠ {node.gate!r} на схеме")
        if element.kind != node.kind:
            report.errors.append(f"{node.id}: тип {element.kind!r} ≠ {node.kind!r} на схеме")
    for extra in sorted(set(registry.elements) - set(ref.nodes)):
        report.errors.append(f"Элемент {extra} отсутствует на эталонной схеме")

    edges = registry.edges()
    for a, b in sorted(ref.edges - edges):
        report.errors.append(f"Стрелка {a} → {b} есть на схеме, но нет контракта")
    for a, b in sorted(edges - ref.edges):
        report.errors.append(f"Контракт {a} → {b} отсутствует на схеме")

    loops = registry.loop_edges()
    for a, b in sorted(ref.loops - loops):
        report.errors.append(f"Петля {a} → {b} есть на схеме, но не реализована")
    drawn = registry.loop_edges(reference_only=True)
    for a, b in sorted(drawn - ref.loops):
        report.errors.append(f"Петля {a} → {b} помечена как эталонная, но на схеме её нет")
    for a, b in sorted(loops - ref.loops):
        report.notes.append(f"Уточнение сверх схемы: петля {a} → {b}")
    return report


def find_reference(start: str | Path | None = None) -> Path | None:
    """Найти эталон рядом с рабочей папкой или выше по дереву."""
    here = Path(start or Path.cwd()).resolve()
    for folder in (here, *here.parents):
        candidate = folder / REFERENCE_FILE
        if candidate.exists():
            return candidate
    return None
