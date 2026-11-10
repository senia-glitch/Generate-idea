"""Система построена по эталонной схеме и эталон не изменён."""

from conftest import REFERENCE

from reqpipe.reference import REFERENCE_SHA256, check, parse_reference


def test_reference_file_is_unchanged():
    assert parse_reference(REFERENCE).sha256 == REFERENCE_SHA256


def test_every_card_lane_edge_and_loop_is_implemented(registry):
    report = check(registry, REFERENCE)
    assert report.ok, "\n".join(report.errors)


def test_reference_sizes(registry):
    ref = parse_reference(REFERENCE)
    assert len(ref.nodes) == len(registry.elements) == 32
    assert ref.edges == registry.edges()
    assert ref.loops <= registry.loop_edges()


def test_each_lane_is_one_domain(registry):
    ref = parse_reference(REFERENCE)
    phases = {n.phase for n in ref.nodes.values()}
    assert phases == {d.phase for d in registry.domains.values()}
    assert len({d.phase for d in registry.domains.values()}) == len(registry.domains)
