from pathlib import Path

import pytest

from reqpipe.catalog import build_registry
from reqpipe.core.config import RunConfig
from reqpipe.domains.platform.knowledge_base import Workspace
from reqpipe.domains.platform.orchestrator import Engine
from reqpipe.executors import make_executor

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "requirements-pipeline.html"
IDEA = "Хочу сервис для учёта домашних финансов — но умнее всего, что есть сейчас"


@pytest.fixture
def registry():
    return build_registry()


@pytest.fixture
def make_engine(tmp_path, registry):
    def factory(**config):
        ws = Workspace(tmp_path / "ws")
        ws.init(IDEA, RunConfig(**{"executor": "mock", **config}))
        engine = Engine(registry, ws)
        engine.factory = lambda name: make_executor(name, engine.config)
        return engine
    return factory
