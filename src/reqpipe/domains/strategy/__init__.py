"""Домен «Синтез и стратегия» (p3)."""

from reqpipe.core import Domain
from reqpipe.domains.strategy.gap_analysis import ELEMENT as GAP
from reqpipe.domains.strategy.personas import ELEMENT as PERSONAS
from reqpipe.domains.strategy.value_proposition import ELEMENT as VISION

DOMAIN = Domain(
    id="strategy", phase="p3", name="Синтез и стратегия", note="Где и чем мы будем лучше",
    elements=(GAP, VISION, PERSONAS),
)
