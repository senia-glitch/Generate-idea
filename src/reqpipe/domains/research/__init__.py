"""Домен «Исследование» (p2): четыре агента параллельно, затем проверка фактов."""

from reqpipe.core import Domain
from reqpipe.domains.research.competitors import ELEMENT as COMPETITORS
from reqpipe.domains.research.compliance import ELEMENT as COMPLIANCE
from reqpipe.domains.research.domain_analysis import ELEMENT as DOMAIN_ANALYSIS
from reqpipe.domains.research.fact_check import ELEMENT as FACTCHECK
from reqpipe.domains.research.voice_of_customer import ELEMENT as VOC

DOMAIN = Domain(
    id="research", phase="p2", name="Исследование", note="Четыре агента параллельно, затем проверка фактов",
    elements=(COMPETITORS, VOC, DOMAIN_ANALYSIS, COMPLIANCE, FACTCHECK),
)
