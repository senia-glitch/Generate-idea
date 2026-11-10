"""Домен «Приоритизация и согласование» (p6)."""

from reqpipe.core import Domain
from reqpipe.domains.agreement.debate import ELEMENT as DEBATE
from reqpipe.domains.agreement.feasibility import ELEMENT as FEASIBILITY
from reqpipe.domains.agreement.prioritization import ELEMENT as PRIORITIZE
from reqpipe.domains.agreement.signoff import ELEMENT as SIGNOFF

DOMAIN = Domain(
    id="agreement", phase="p6", name="Приоритизация и согласование", note="Последнее слово — за человеком",
    elements=(FEASIBILITY, PRIORITIZE, DEBATE, SIGNOFF),
)
