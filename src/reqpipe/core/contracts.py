"""Контракты между элементами.

* ``Artifact`` — базовый класс результата элемента (выходной контракт).
* ``Consumes`` — объявление элемента-потребителя: «беру у ``source`` артефакт
  такого-то типа, такие-то поля». Из этих объявлений реестр строит граф.
* ``Loop`` — контракт обратной связи: элемент-фильтр может вернуть работу
  адресату вместе со списком ``FeedbackItem``.
* ``TraceCatalog`` — компактный каталог идентификаторов (боли, обязательства,
  истории, требования…), который передаётся по цепочке контрактов, чтобы
  трассировку можно было проверить в любой точке.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal

from pydantic import BaseModel, ConfigDict, Field


class Artifact(BaseModel):
    """Результат работы элемента. Лишние поля от агента игнорируются."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


class Source(BaseModel):
    """Источник утверждения: ссылка, название, цитата."""

    model_config = ConfigDict(extra="ignore")

    title: str = ""
    url: str = ""
    quote: str = Field("", description="Короткая цитата из источника, подтверждающая утверждение")
    accessed: str = Field("", description="Дата обращения, ГГГГ-ММ-ДД")


Severity = Literal["critical", "major", "minor"]


class FeedbackItem(BaseModel):
    """Замечание фильтра качества, адресованное элементу на доработку."""

    model_config = ConfigDict(extra="ignore")

    id: str = ""
    severity: Severity = "major"
    target: str = Field("", description="ID элемента, который должен исправить замечание; пусто — адресат по умолчанию")
    refs: list[str] = Field(default_factory=list, description="ID затронутых сущностей: FR-001, PAIN-003 …")
    problem: str
    suggestion: str = ""


class GateReport(Artifact):
    """Общая часть отчёта любого фильтра качества (quality gate)."""

    verdict: Literal["pass", "fail"]
    summary: str = ""
    findings: list[FeedbackItem] = Field(default_factory=list)


# --------------------------------------------------------------------------- каталог трассировки

class CatalogItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    title: str = ""
    severity: int | None = None
    refs: list[str] = Field(default_factory=list, description="ID, на которые ссылается элемент")
    data: dict[str, Any] = Field(default_factory=dict)


class TraceCatalog(BaseModel):
    """Каталог ID по видам: pain, job, obligation, entity, rule, story, …"""

    model_config = ConfigDict(extra="ignore")

    items: dict[str, list[CatalogItem]] = Field(default_factory=dict)

    def add(self, kind: str, items: Iterable[CatalogItem]) -> "TraceCatalog":
        bucket = {i.id: i for i in self.items.get(kind, [])}
        for item in items:
            bucket[item.id] = item
        self.items[kind] = list(bucket.values())
        return self

    def merge(self, other: "TraceCatalog | dict | None") -> "TraceCatalog":
        if other is None:
            return self
        if isinstance(other, dict):
            other = TraceCatalog.model_validate(other)
        for kind, items in other.items.items():
            self.add(kind, items)
        return self

    def ids(self, kind: str) -> list[str]:
        return [i.id for i in self.items.get(kind, [])]

    def get(self, kind: str) -> list[CatalogItem]:
        return list(self.items.get(kind, []))

    @classmethod
    def combine(cls, *catalogs: "TraceCatalog | dict | None") -> "TraceCatalog":
        result = cls()
        for c in catalogs:
            result.merge(c)
        return result


# --------------------------------------------------------------------------- объявления связей

@dataclass(frozen=True)
class Consumes:
    """Входной контракт элемента: что он берёт и у кого."""

    source: str
    model: type[Artifact]
    fields: tuple[str, ...] = ()
    note: str = ""


@dataclass(frozen=True)
class Loop:
    """Контракт обратной связи «фильтр → элемент на доработку»."""

    target: str
    label: str
    in_reference: bool = True  # нарисована ли эта петля на эталонной схеме


@dataclass(frozen=True)
class Contract:
    """Ребро графа, выведенное реестром из ``Consumes``."""

    source: str
    target: str
    model: type[Artifact]
    fields: tuple[str, ...] = ()
    note: str = ""

    def project(self, data: dict[str, Any]) -> dict[str, Any]:
        """Оставить в артефакте только поля, оговорённые контрактом."""
        if not self.fields:
            return dict(data)
        return {k: data[k] for k in self.fields if k in data}

    @property
    def key(self) -> tuple[str, str]:
        return (self.source, self.target)
