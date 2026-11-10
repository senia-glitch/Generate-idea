"""Реестр: собирает домены, выводит граф контрактов и проверяет правила.

Правила:
1. ID элементов уникальны во всей системе.
2. Связь между элементами существует только как контракт (``Consumes``),
   и тип артефакта в контракте обязан совпадать с выходным контрактом источника.
3. Прямые контракты образуют ациклический граф; петли доработки (``Loop``)
   могут вести только «назад» — к элементу выше по потоку.
4. Элементы сквозного слоя (service) не участвуют в прямом потоке.
"""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Iterable

from reqpipe.core.contracts import Contract, Loop
from reqpipe.core.domain import Domain
from reqpipe.core.element import Element
from reqpipe.core.errors import RegistryError


class Registry:
    def __init__(self, domains: Iterable[Domain]):
        self.domains: dict[str, Domain] = {}
        self.elements: dict[str, Element] = {}
        for domain in domains:
            if domain.id in self.domains:
                raise RegistryError(f"Домен {domain.id} объявлен дважды")
            self.domains[domain.id] = domain
            for element in domain.elements:
                if element.id in self.elements:
                    raise RegistryError(f"Элемент {element.id} объявлен дважды")
                self.elements[element.id] = element

        self.contracts: list[Contract] = [
            Contract(c.source, e.id, c.model, c.fields, c.note)
            for e in self.elements.values()
            for c in e.consumes
        ]
        self.loops: list[tuple[str, Loop]] = [
            (e.id, loop) for e in self.elements.values() for loop in e.loops
        ]
        self._incoming: dict[str, list[Contract]] = defaultdict(list)
        self._outgoing: dict[str, list[Contract]] = defaultdict(list)
        for c in self.contracts:
            self._incoming[c.target].append(c)
            self._outgoing[c.source].append(c)
        self.order: list[str] = self._validate_and_sort()

    # ------------------------------------------------------------------ доступ

    def element(self, element_id: str) -> Element:
        try:
            return self.elements[element_id]
        except KeyError:
            raise RegistryError(f"Неизвестный элемент: {element_id}") from None

    def incoming(self, element_id: str) -> list[Contract]:
        return list(self._incoming.get(element_id, []))

    def outgoing(self, element_id: str) -> list[Contract]:
        return list(self._outgoing.get(element_id, []))

    @property
    def stages(self) -> list[Element]:
        """Элементы прямого потока в топологическом порядке."""
        return [self.elements[i] for i in self.order]

    @property
    def services(self) -> list[Element]:
        return [e for e in self.elements.values() if e.mode == "service"]

    def downstream(self, element_id: str) -> list[str]:
        """Все элементы ниже по потоку (транзитивно), в топологическом порядке."""
        seen: set[str] = set()
        queue = deque([element_id])
        while queue:
            cur = queue.popleft()
            for c in self._outgoing.get(cur, []):
                if c.target not in seen:
                    seen.add(c.target)
                    queue.append(c.target)
        return [i for i in self.order if i in seen]

    def upstream(self, element_id: str) -> set[str]:
        seen: set[str] = set()
        queue = deque([element_id])
        while queue:
            cur = queue.popleft()
            for c in self._incoming.get(cur, []):
                if c.source not in seen:
                    seen.add(c.source)
                    queue.append(c.source)
        return seen

    def edges(self) -> set[tuple[str, str]]:
        return {c.key for c in self.contracts}

    def loop_edges(self, reference_only: bool = False) -> set[tuple[str, str]]:
        return {(src, l.target) for src, l in self.loops if l.in_reference or not reference_only}

    # ------------------------------------------------------------------ проверки

    def _validate_and_sort(self) -> list[str]:
        for c in self.contracts:
            if c.source not in self.elements:
                raise RegistryError(f"{c.target}: контракт ссылается на неизвестный источник {c.source}")
            src = self.elements[c.source]
            dst = self.elements[c.target]
            if src.mode == "service" or dst.mode == "service":
                raise RegistryError(f"{c.source}→{c.target}: сервисы сквозного слоя не участвуют в прямом потоке")
            if src.output is None or not issubclass(src.output, c.model):
                raise RegistryError(
                    f"{c.source}→{c.target}: тип контракта {c.model.__name__} не совпадает "
                    f"с выходом источника {getattr(src.output, '__name__', None)}"
                )
            unknown = [f for f in c.fields if f not in src.output.model_fields]
            if unknown:
                raise RegistryError(f"{c.source}→{c.target}: в контракте неизвестные поля {unknown}")

        stage_ids = [e.id for e in self.elements.values() if e.mode != "service"]
        indeg = {i: 0 for i in stage_ids}
        for c in self.contracts:
            indeg[c.target] += 1
        queue = deque(i for i in stage_ids if indeg[i] == 0)
        order: list[str] = []
        while queue:
            cur = queue.popleft()
            order.append(cur)
            for c in self._outgoing.get(cur, []):
                indeg[c.target] -= 1
                if indeg[c.target] == 0:
                    queue.append(c.target)
        if len(order) != len(stage_ids):
            cyclic = sorted(set(stage_ids) - set(order))
            raise RegistryError(f"Прямые контракты образуют цикл: {cyclic}")

        position = {i: n for n, i in enumerate(order)}
        for src, loop in self.loops:
            if loop.target not in self.elements:
                raise RegistryError(f"{src}: петля ведёт к неизвестному элементу {loop.target}")
            if position[loop.target] >= position[src]:
                raise RegistryError(f"{src}→{loop.target}: петля доработки должна вести вверх по потоку")
            if loop.target not in self.upstream(src):
                raise RegistryError(f"{src}→{loop.target}: адресат петли не связан с фильтром контрактами")
        for element in self.elements.values():
            if element.mode == "agent" and element.response_model is None:
                raise RegistryError(f"{element.id}: у элемента-агента нет выходного контракта")
        return order
