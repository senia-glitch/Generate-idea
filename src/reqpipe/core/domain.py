"""Домен — одна фаза (дорожка) эталонной схемы."""

from __future__ import annotations

from dataclasses import dataclass

from reqpipe.core.element import Element


@dataclass
class Domain:
    id: str            # имя пакета: research, quality …
    phase: str         # ID дорожки на эталонной схеме: p0 … p7, px
    name: str          # «Исследование», «Каскад проверок качества» …
    note: str
    elements: tuple[Element, ...]
    service: bool = False   # сквозной слой: элементы-сервисы без контрактов

    def __post_init__(self) -> None:
        for element in self.elements:
            element.domain = self.id

    def element(self, element_id: str) -> Element:
        for e in self.elements:
            if e.id == element_id:
                return e
        raise KeyError(element_id)
