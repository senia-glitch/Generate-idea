"""Домен «Вход» (p0): приём сырой идеи."""

from reqpipe.core import Domain
from reqpipe.domains.intake.idea import ELEMENT as IDEA

DOMAIN = Domain(
    id="intake", phase="p0", name="Замысел", note="Что угодно и в любом виде",
    elements=(IDEA,),
)
