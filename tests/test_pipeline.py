"""Полные прогоны конвейера на mock-исполнителе."""

import json

import pytest

from reqpipe.core.errors import ContractViolation, StateError
from reqpipe.executors.base import ExecutionResult
from reqpipe.executors.mock import MockExecutor


def test_autonomous_run_completes_with_loop(make_engine):
    engine = make_engine(autonomous=True)
    report = engine.run()
    assert report.stop.kind == "complete", report.stop
    assert engine.state.loop_counts == {"quality->reqwriter": 1}       # демонстрационный возврат G1 → 4.3
    assert engine.st("reqwriter").version == 2
    srs = engine.ws.path("output/SRS.md").read_text(encoding="utf-8")
    assert "FR-001" in srs and "Матрица трассируемости" in srs and "НЕ ПОКРЫТО" not in srs
    baseline = engine.ws.load_artifact("signoff")
    assert baseline["approved"] and baseline["approved_by"] == "arbiter"
    assert all(fr["status"] == "approved" for fr in baseline["spec"]["requirements"])
    decided = {d["element_id"] for d in engine.ws.decisions()}
    assert {"clarify", "factcheck", "vision", "feasibility", "debate", "signoff"} <= decided
    assert any("синтетические" in f for f in engine.ws.load_artifact("srs")["flags"])
    assert engine.ws.path("output/tests/fr-001.spec.ts").exists()
    assert engine.ws.path("output/prototype/index.html").exists()
    assert json.loads(engine.ws.read_text("output/trace.json"))["edges"]


def test_human_mode_stops_at_checkpoints_and_continues_after_approval(make_engine):
    engine = make_engine()
    report = engine.run()
    assert report.stop.kind == "approval" and report.stop.element == "clarify"
    engine.approve("clarify", "ок")
    report = engine.run(approver=lambda action: ("approve", ""))
    assert report.stop.kind == "complete"
    assert engine.ws.load_artifact("signoff")["approved_by"] == "human"


def test_reject_reruns_element_with_feedback(make_engine):
    engine = make_engine()
    engine.run()
    engine.reject("clarify", "Уточни аудиторию")
    st = engine.st("clarify")
    assert st.status == "pending" and st.feedback[0]["problem"] == "Уточни аудиторию"
    task = engine.prepare("clarify")
    assert "Уточни аудиторию" in task.prompt and "Доработка" in task.prompt


def test_manual_agent_flow_with_contract_violation(make_engine):
    engine = make_engine(executor="manual", autonomous=True)
    action = engine.next_action()
    assert action.kind == "task" and action.element == "clarify"
    with pytest.raises(ContractViolation):
        engine.submit("clarify", {"goal": "только цель"})          # нет обязательного поля problem
    assert engine.st("clarify").repairs == 1
    good = engine.reg.element("clarify").example(engine.context("clarify"))
    engine.submit("clarify", json.dumps(good, ensure_ascii=False))
    assert engine.st("clarify").status == "done"
    assert engine.next_action().element == "frame"


def test_submit_is_rejected_when_not_expected(make_engine):
    engine = make_engine(executor="manual")
    with pytest.raises(StateError):
        engine.submit("benchmark", {})


class AlwaysFailQuality(MockExecutor):
    def execute(self, task):
        result = super().execute(task)
        if task.element_id == "quality":
            result.data = {**result.data, "verdict": "fail",
                           "findings": [{"severity": "major", "problem": "Всё ещё размыто", "target": "reqwriter"}]}
        return result


def _always_fail(engine):
    engine.factory = lambda name: AlwaysFailQuality(engine.config.executors["mock"])


def test_loop_budget_in_human_mode_asks_for_decision(make_engine):
    engine = make_engine(autonomous=True, max_loop_iterations=2)
    engine.config.autonomous = False
    engine.config.elements = {}
    _always_fail(engine)
    report = engine.run(approver=lambda a: ("approve", "") if a.data.get("checkpoint") == "approval" else ("quit", ""))
    assert report.stop.kind == "approval" and report.stop.data["checkpoint"] == "loop_budget"
    assert engine.state.loop_counts["quality->reqwriter"] == 2
    engine.approve("quality", "принимаем риск")
    assert engine.st("quality").status == "done"
    assert any("принят с замечаниями" in f for f in engine.state.flags)


def test_loop_budget_in_autonomous_mode_accepts_noncritical(make_engine):
    engine = make_engine(autonomous=True, max_loop_iterations=1)
    _always_fail(engine)
    report = engine.run()
    assert report.stop.kind == "complete"
    flags = engine.ws.load_artifact("srs")["flags"]
    assert any("G1" in f and "принят с замечаниями" in f for f in flags)


def test_external_stage_waits_for_results_and_can_be_waived(make_engine):
    engine = make_engine(autonomous=True)
    engine.config.elements = {}
    engine.config.executors["mock"].fail_once = []
    report = engine.run(until="simulation")
    assert engine.st("simulation").status == "done"
    engine.config.executor = "manual"
    action = engine.next_action()
    assert action.kind == "task" and action.element == "usertest"
    plan = engine.reg.element("usertest").example(engine.context("usertest"))
    action = engine.submit("usertest", plan)
    assert action.kind == "external" and engine.st("usertest").status == "awaiting_external"
    with pytest.raises(StateError):
        engine.waive("usertest", "нет бюджета", by="arbiter")      # арбитру пропускать тест запрещено
    engine.waive("usertest", "нет бюджета на рекрутинг")
    spec = engine.ws.load_artifact("usertest")["spec"]
    assert any("не проведена" in f for f in spec["flags"])


def test_parallel_research_stage(make_engine):
    engine = make_engine(autonomous=True, parallel=4)
    report = engine.run()
    assert report.stop.kind == "complete"


def test_context_pack_is_compressed_to_budget(make_engine):
    engine = make_engine(autonomous=True, context_budget_chars=1500)
    engine.run(until="testgen")
    task = engine.prepare("quality")
    assert "Менеджер контекста сократил пакет" in task.prompt
