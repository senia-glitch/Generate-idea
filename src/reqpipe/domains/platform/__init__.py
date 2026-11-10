"""Сквозной слой (px): оркестратор, менеджер контекста, база знаний, трассировка, контрольные точки.

Элементы этого домена — сервисы: они не участвуют в прямом потоке
контрактов, а обслуживают все фазы.
"""

from reqpipe.core import Domain
from reqpipe.domains.platform.checkpoints import ELEMENT as HITL
from reqpipe.domains.platform.context_manager import ELEMENT as CTX
from reqpipe.domains.platform.knowledge_base import ELEMENT as KB
from reqpipe.domains.platform.orchestrator import ELEMENT as ORCH
from reqpipe.domains.platform.traceability import ELEMENT as TRACE

DOMAIN = Domain(
    id="platform", phase="px", name="Инфраструктура процесса", note="Обслуживает все фазы конвейера",
    elements=(ORCH, CTX, KB, TRACE, HITL), service=True,
)
