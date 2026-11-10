"""Каркас: контракты, элементы (карточки), домены и реестр.

Ядро ничего не знает о конкретных фазах конвейера — оно задаёт только правила:
связь между элементами существует, только если её описывает контракт.
"""

from reqpipe.core.contracts import (
    Artifact,
    CatalogItem,
    Consumes,
    Contract,
    FeedbackItem,
    GateReport,
    Loop,
    Source,
    TraceCatalog,
)
from reqpipe.core.domain import Domain
from reqpipe.core.element import Context, Element, GateOutcome, Instructions
from reqpipe.core.registry import Registry

__all__ = [
    "Artifact", "CatalogItem", "Consumes", "Contract", "Context", "Domain", "Element",
    "FeedbackItem", "GateOutcome", "GateReport", "Instructions", "Loop", "Registry",
    "Source", "TraceCatalog",
]
