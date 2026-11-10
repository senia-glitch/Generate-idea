"""Домен «Результат» (p7): сборка спецификации функциональных требований."""

from reqpipe.core import Domain
from reqpipe.domains.result.srs import ELEMENT as SRS

DOMAIN = Domain(
    id="result", phase="p7", name="Результат", note="Готовая спецификация",
    elements=(SRS,),
)
