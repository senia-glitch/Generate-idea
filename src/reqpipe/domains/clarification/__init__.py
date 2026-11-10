"""Домен «Прояснение замысла» (p1)."""

from reqpipe.core import Domain
from reqpipe.domains.clarification.framing import ELEMENT as FRAME
from reqpipe.domains.clarification.interview import ELEMENT as CLARIFY

DOMAIN = Domain(
    id="clarification", phase="p1", name="Прояснение замысла", note="Диалог агента с автором идеи",
    elements=(CLARIFY, FRAME),
)
