"""Домен «Формализация требований» (p4)."""

from reqpipe.core import Domain
from reqpipe.domains.formalization.acceptance import ELEMENT as ACCEPTANCE
from reqpipe.domains.formalization.data_model import ELEMENT as MODEL
from reqpipe.domains.formalization.requirements_writer import ELEMENT as REQWRITER
from reqpipe.domains.formalization.story_map import ELEMENT as STORYMAP
from reqpipe.domains.formalization.test_generation import ELEMENT as TESTGEN

DOMAIN = Domain(
    id="formalization", phase="p4", name="Формализация требований", note="От историй к строгой спецификации",
    elements=(STORYMAP, MODEL, REQWRITER, ACCEPTANCE, TESTGEN),
)
