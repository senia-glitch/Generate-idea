"""Правила реестра: связи — только контракты, типы совпадают, петли ведут вверх по потоку."""

import ast
from pathlib import Path

import pytest

from reqpipe.core import Artifact, Consumes, Domain, Element, Instructions, Loop, Registry
from reqpipe.core.errors import RegistryError

DOMAINS_DIR = Path(__file__).resolve().parents[1] / "src" / "reqpipe" / "domains"


class A(Artifact):
    x: int = 0


class B(Artifact):
    y: int = 0


def _el(eid, consumes=(), loops=(), output=A):
    return Element(id=eid, num=eid, title=eid, actor="", kind="agent", instructions=Instructions(purpose=""),
                   consumes=consumes, loops=loops, output=output)


def test_contract_type_must_match_source_output():
    d = Domain("d", "p1", "D", "", (_el("a"), _el("b", consumes=(Consumes("a", B),))))
    with pytest.raises(RegistryError, match="не совпадает"):
        Registry([d])


def test_unknown_contract_field_is_rejected():
    d = Domain("d", "p1", "D", "", (_el("a"), _el("b", consumes=(Consumes("a", A, ("nope",)),))))
    with pytest.raises(RegistryError, match="неизвестные поля"):
        Registry([d])


def test_cycles_are_rejected():
    d = Domain("d", "p1", "D", "", (_el("a", consumes=(Consumes("b", A),)), _el("b", consumes=(Consumes("a", A),))))
    with pytest.raises(RegistryError, match="цикл"):
        Registry([d])


def test_loop_must_point_upstream():
    d = Domain("d", "p1", "D", "", (_el("a", loops=(Loop("b", "x"),)), _el("b", consumes=(Consumes("a", A),))))
    with pytest.raises(RegistryError, match="вверх по потоку"):
        Registry([d])


def test_duplicate_element_ids_are_rejected():
    with pytest.raises(RegistryError, match="дважды"):
        Registry([Domain("d1", "p1", "D", "", (_el("a"),)), Domain("d2", "p2", "D", "", (_el("a"),))])


def test_every_agent_element_has_instructions_and_contract(registry):
    for element in registry.elements.values():
        assert element.instructions.purpose, element.id
        if element.mode == "agent":
            assert element.response_model is not None, element.id
            assert element.example is not None, f"{element.id}: нет эталонного ответа для mock"


def test_domains_import_only_public_contracts_of_other_domains():
    """Изоляция доменов: из чужого домена можно импортировать только его contracts."""
    violations = []
    for path in DOMAINS_DIR.rglob("*.py"):
        own = path.relative_to(DOMAINS_DIR).parts[0]
        if own == "__init__.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("reqpipe.domains."):
                parts = node.module.split(".")
                other = parts[2]
                if other != own and parts[3:] != ["contracts"]:
                    violations.append(f"{path.name}: from {node.module}")
    assert not violations, violations
