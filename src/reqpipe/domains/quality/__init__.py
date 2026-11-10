"""Домен «Каскад проверок качества» (p5): G1 → G6."""

from reqpipe.core import Domain
from reqpipe.domains.quality.benchmark import ELEMENT as BENCHMARK
from reqpipe.domains.quality.coverage import ELEMENT as COVERAGE
from reqpipe.domains.quality.linter import ELEMENT as QUALITY
from reqpipe.domains.quality.red_team import ELEMENT as CRITIC
from reqpipe.domains.quality.simulation import ELEMENT as SIMULATION
from reqpipe.domains.quality.user_testing import ELEMENT as USERTEST

DOMAIN = Domain(
    id="quality", phase="p5", name="Каскад проверок качества", note="Шесть последовательных quality gates",
    elements=(QUALITY, CRITIC, COVERAGE, SIMULATION, USERTEST, BENCHMARK),
)
