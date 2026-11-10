"""Сборка системы: все домены в порядке фаз эталонной схемы."""

from __future__ import annotations

from functools import lru_cache

from reqpipe.core import Registry


@lru_cache(maxsize=1)
def build_registry() -> Registry:
    from reqpipe.domains import (agreement, clarification, formalization, intake, platform, quality, research,
                                 result, strategy)
    return Registry([
        intake.DOMAIN, clarification.DOMAIN, research.DOMAIN, strategy.DOMAIN, formalization.DOMAIN,
        quality.DOMAIN, agreement.DOMAIN, result.DOMAIN, platform.DOMAIN,
    ])
