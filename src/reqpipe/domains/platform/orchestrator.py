"""Оркестратор процесса: ведёт граф этапов по контрактам.

Состояния элемента: pending → in_progress → (awaiting_external) → done,
а также awaiting_approval (контрольная точка) и failed.
Элемент готов к запуску, когда все его источники по контрактам в статусе done.

Петли доработки: фильтр, не пройдя проверку, возвращает замечания адресату;
адресат и всё ниже него по потоку сбрасываются в pending. Бюджет возвратов
на каждую петлю — ``max_loop_iterations``; когда он исчерпан, решает человек
или (в автономном режиме) агент-арбитр.
"""

from __future__ import annotations

import json
import shlex
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pydantic import ValidationError

from reqpipe.core import Context, Element, FeedbackItem, GateOutcome, Instructions, Registry
from reqpipe.core.errors import ContractViolation, ExecutorError, StateError
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.platform.checkpoints import Checkpoints, summarize
from reqpipe.domains.platform.context_manager import build_pack, render_task
from reqpipe.domains.platform.contracts import ArbiterVerdict, CheckpointDecision
from reqpipe.domains.platform.knowledge_base import ElementState, Workspace, now
from reqpipe.domains.platform.traceability import build_graph
from reqpipe.executors.base import Executor, Task

ExecutorFactory = Callable[[str], Executor]
Approver = Callable[["Action"], tuple[str, str]]


@dataclass
class Action:
    """Следующее действие конвейера — то, что видит агент или человек."""

    kind: str          # task | approval | external | complete | failed | stopped | blocked | done | looped
    element: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"action": self.kind, "element": self.element, **self.data}


@dataclass
class RunReport:
    steps: list[str] = field(default_factory=list)
    stop: Action | None = None
    cost_usd: float = 0.0


def _errors(exc: ValidationError) -> list[str]:
    return [f"{'.'.join(str(p) for p in e['loc']) or '<корень>'}: {e['msg']}" for e in exc.errors()]


class Engine:
    def __init__(self, registry: Registry, workspace: Workspace, executor_factory: ExecutorFactory | None = None):
        self.reg = registry
        self.ws = workspace
        self.config = workspace.load_config()
        self.state = workspace.load_state()
        self.factory = executor_factory
        self.checkpoints = Checkpoints(workspace, self.config)
        self._lock = threading.RLock()
        for element in registry.stages:
            self.state.elements.setdefault(element.id, ElementState())

    # ================================================================== состояние

    def save(self) -> None:
        self.ws.save_state(self.state)

    def st(self, element_id: str) -> ElementState:
        return self.state.elements[element_id]

    def _set(self, element_id: str, status: str, **fields: Any) -> None:
        st = self.st(element_id)
        st.status = status
        st.updated_at = now()
        for k, v in fields.items():
            setattr(st, k, v)

    def is_ready(self, element_id: str) -> bool:
        return self.st(element_id).status == "pending" and all(
            self.st(c.source).status == "done" for c in self.reg.incoming(element_id))

    def first(self, status: str) -> str | None:
        return next((e.id for e in self.reg.stages if self.st(e.id).status == status), None)

    def is_complete(self) -> bool:
        return all(self.st(e.id).status == "done" for e in self.reg.stages)

    # ================================================================== контекст

    def inputs(self, element_id: str) -> dict[str, dict]:
        result = {}
        for c in self.reg.incoming(element_id):
            artifact = self.ws.load_artifact(c.source)
            if artifact is None:
                raise StateError(f"{element_id}: нет артефакта источника {c.source}")
            result[c.source] = c.project(artifact)
        return result

    def context(self, element_id: str) -> Context:
        st = self.st(element_id)
        return Context(
            element=self.reg.element(element_id),
            inputs=self.inputs(element_id),
            feedback=[FeedbackItem.model_validate(f) for f in st.feedback],
            iteration=st.version,
            loop_counts=dict(self.state.loop_counts),
            autonomous=self.config.autonomous,
            config=self.config,
            idea_text=self.ws.idea_text(),
            output_writer=self.ws.output_writer,
        )

    # ================================================================== задачи

    def prepare(self, element_id: str, repair_errors: list[str] | None = None) -> Task:
        """Собрать пакет контекста и задачу для агента; элемент переходит в in_progress."""
        with self._lock:
            element = self.reg.element(element_id)
            if element.mode not in ("agent", "external"):
                raise StateError(f"{element_id}: элемент выполняется без агента")
            st = self.st(element_id)
            if st.status not in ("pending", "in_progress"):
                raise StateError(f"{element_id}: нельзя выдать задачу в статусе {st.status}")
            if st.status == "pending" and not self.is_ready(element_id):
                raise StateError(f"{element_id}: ещё не готовы источники по контрактам")
            ctx = self.context(element_id)
            pack = build_pack(element_id, ctx.inputs, self.config.context_budget_chars)
            prepared = element.prepare(ctx) if element.prepare else None
            schema = element.response_model.model_json_schema()
            version = st.version + 1
            suffix = f".repair{st.repairs}" if repair_errors else ""
            task_rel = f"tasks/{element_id}.v{version}{suffix}.md"
            result_file = self.ws.path(f"results/{element_id}.json")
            if result_file.exists() and not repair_errors:
                result_file.unlink()
            text = render_task(
                element, self.reg.incoming(element_id), pack, schema=schema, result_file=str(result_file),
                domain_name=self.reg.domains[element.domain].name,
                feedback=ctx.feedback, iteration=ctx.iteration, autonomous=self.config.autonomous,
                prepared=prepared, repair_errors=repair_errors,
            )
            self.ws.write_text(task_rel, text)
            self.ws.write_json(f"schemas/{element_id}.json", schema)
            if st.status == "pending":
                st.runs += 1
            self._set(element_id, "in_progress", task_file=task_rel, schema_file=f"schemas/{element_id}.json",
                      result_file=f"results/{element_id}.json")
            self.state.log("task", element_id, version=version, repair=bool(repair_errors))
            self.save()
            executor = self.config.executor_for(element_id)
            cfg = self.config.executors.get(executor)
            return Task(
                element_id=element_id, title=element.title, workspace=self.ws.root,
                task_file=self.ws.path(task_rel), schema=schema, schema_file=self.ws.path(f"schemas/{element_id}.json"),
                result_file=result_file, prompt=text, capabilities=element.capabilities,
                model=self.config.model_for(element_id, executor),
                extra_args=self.config.extra_args_for(element_id, executor),
                timeout_sec=cfg.timeout_sec if cfg else 1800, context=ctx,
                log_file=self.ws.path(f"logs/{element_id}.v{version}{suffix}.{executor}.log"),
            )

    def submit(self, element_id: str, payload: dict | str, cost: float = 0.0) -> Action:
        """Принять ответ агента: проверить контракт, собрать артефакт, применить фильтр и контрольную точку."""
        with self._lock:
            element = self.reg.element(element_id)
            st = self.st(element_id)
            if st.status == "pending" and self.is_ready(element_id):
                st.runs += 1
            elif st.status != "in_progress":
                raise StateError(f"{element_id}: ответ не ожидается (статус {st.status})")
            data = json.loads(payload) if isinstance(payload, str) else payload
            if not isinstance(data, dict):
                raise ContractViolation(element_id, ["ответ должен быть JSON-объектом"])
            try:
                validated = element.response_model.model_validate(data).model_dump(mode="json")
            except ValidationError as exc:
                st.repairs += 1
                st.last_error = "; ".join(_errors(exc))[:2000]
                st.cost_usd += cost
                self.save()
                raise ContractViolation(element_id, _errors(exc)) from None
            st.cost_usd += cost
            if element.mode == "external":
                plan = element.on_plan(self.context(element_id), validated) if element.on_plan else validated
                self._set(element_id, "awaiting_external", plan=plan, repairs=0, last_error="")
                self.state.log("plan", element_id)
                self.save()
                return self._external_action(element_id)
            return self._complete(element_id, validated)

    def submit_external(self, element_id: str, payload: dict | str, by: str = "human") -> Action:
        """Результаты внешнего этапа (сессии с людьми)."""
        with self._lock:
            element = self.reg.element(element_id)
            st = self.st(element_id)
            if st.status != "awaiting_external" or element.external_model is None:
                raise StateError(f"{element_id}: внешние результаты не ожидаются (статус {st.status})")
            data = json.loads(payload) if isinstance(payload, str) else payload
            try:
                results = element.external_model.model_validate(data).model_dump(mode="json")
            except ValidationError as exc:
                raise ContractViolation(element_id, _errors(exc)) from None
            self.state.log("external_results", element_id, by=by)
            return self._complete(element_id, {"plan": st.plan or {}, "results": results})

    def waive(self, element_id: str, reason: str, by: str = "human") -> Action:
        """Явно пропустить внешний этап. Решение записывается в журнал и в спецификацию."""
        with self._lock:
            st = self.st(element_id)
            if st.status != "awaiting_external":
                raise StateError(f"{element_id}: пропуск возможен только для ожидающего внешнего этапа")
            if by == "arbiter" and not self.config.allow_waive_user_test:
                raise StateError("Арбитру запрещено пропускать тест с людьми (allow_waive_user_test = false)")
            self.checkpoints.record(CheckpointDecision(element_id=element_id, kind="external_waiver", decision="waive",
                                                       by=by, comment=reason, at=now()))
            return self._complete(element_id, {"plan": st.plan or {}, "results": None, "waived": True,
                                               "waiver_reason": reason})

    # ================================================================== внутренняя механика

    def _complete(self, element_id: str, agent_data: dict) -> Action:
        element = self.reg.element(element_id)
        st = self.st(element_id)
        ctx = self.context(element_id)
        data = element.finalize(ctx, agent_data) if element.finalize else agent_data
        try:
            artifact = element.output.model_validate(data).model_dump(mode="json")
        except ValidationError as exc:
            raise ContractViolation(element_id, ["сборка артефакта: " + e for e in _errors(exc)]) from None
        st.version += 1
        self.ws.save_artifact(element_id, st.version, artifact)
        st.feedback, st.repairs, st.last_error, st.plan = [], 0, "", None
        self.state.log("artifact", element_id, version=st.version)
        self._update_trace()

        outcome = self._evaluate(element, ctx, artifact)
        if outcome is not None and not outcome.passed:
            return self._handle_failure(element_id, outcome)
        if outcome is not None:
            self.state.log("gate_passed", element_id, gate=element.gate or "")
        return self._after_pass(element_id, artifact)

    def _after_pass(self, element_id: str, artifact: dict) -> Action:
        element = self.reg.element(element_id)
        if element.checkpoint:
            if self.config.autonomous:
                decision = self._arbiter(element, artifact)
                key = f"arbiter->{element_id}"
                if decision.decision == "reject" and self.state.loop_counts.get(key, 0) >= self.config.max_loop_iterations:
                    decision = decision.model_copy(update={
                        "decision": "approve", "low_confidence": True,
                        "comment": f"Бюджет возвратов арбитра исчерпан, принято с низкой уверенностью: {decision.comment}"})
                self.checkpoints.record(decision)
                if decision.decision == "approve":
                    return self._approve(element_id, decision.model_dump())
                self.state.loop_counts[key] = self.state.loop_counts.get(key, 0) + 1
                return self._rerun(element_id, f"Арбитр вернул на доработку: {decision.comment}")
            self._set(element_id, "awaiting_approval", checkpoint="approval")
            self.save()
            return self._approval_action(element_id)
        self._set(element_id, "done", checkpoint="")
        self.save()
        return Action("done", element_id)

    def _evaluate(self, element: Element, ctx: Context, artifact: dict) -> GateOutcome | None:
        if element.evaluate is not None:
            return element.evaluate(ctx, artifact)
        if element.loops and "verdict" in artifact:
            return evaluate_verdict(ctx, artifact)
        return None

    def _invalidate(self, element_ids: list[str]) -> None:
        for d in element_ids:
            ds = self.st(d)
            if ds.status != "pending" or ds.checkpoint:
                self._set(d, "pending", checkpoint="", plan=None)

    def _handle_failure(self, element_id: str, outcome: GateOutcome) -> Action:
        element = self.reg.element(element_id)
        active, exhausted = [], []
        for target, items in outcome.feedback.items():
            key = f"{element_id}->{target}"
            (exhausted if self.state.loop_counts.get(key, 0) >= self.config.max_loop_iterations else active).append(
                (target, [i.model_dump() for i in items]))
        if not active:
            findings = [f for _, items in exhausted for f in items]
            if self.config.autonomous:
                decision = self.checkpoints.loop_budget_decision(element, findings)
                self.checkpoints.record(decision)
                if decision.decision == "stop":
                    self._set(element_id, "failed", last_error=decision.comment)
                    self.state.stopped = f"{element.num} {element.title}: {decision.comment}"
                    self.save()
                    return Action("stopped", element_id, {"reason": self.state.stopped})
                return self._accept_with_risk(element_id, findings, by="arbiter")
            self._set(element_id, "awaiting_approval", checkpoint="loop_budget", feedback=findings)
            self.save()
            return self._approval_action(element_id)

        targets = [t for t, _ in active]
        affected = sorted({d for t in targets for d in [t] + self.reg.downstream(t)}, key=self.reg.order.index)
        self._invalidate(affected)
        for target, items in active:
            self.state.loop_counts[f"{element_id}->{target}"] = self.state.loop_counts.get(f"{element_id}->{target}", 0) + 1
            self._set(target, "pending", feedback=items)
        if exhausted:
            self.state.flags.append(f"{element.gate or element.num}: часть замечаний принята без доработки — бюджет исчерпан")
        self.state.log("loop", element_id, targets=targets, findings=sum(len(i) for _, i in active))
        self.save()
        return Action("looped", element_id, {"targets": targets, "summary": outcome.summary})

    def _accept_with_risk(self, element_id: str, findings: list[dict], by: str) -> Action:
        element = self.reg.element(element_id)
        flag = (f"{element.gate or element.num} «{element.title}» принят с замечаниями после исчерпания бюджета "
                f"итераций ({by}): " + "; ".join(f.get("problem", "")[:80] for f in findings[:3]))
        self.state.flags.append(flag)
        artifact = self.ws.load_artifact(element_id) or {}
        if isinstance(artifact.get("spec"), dict):
            artifact["spec"].setdefault("flags", []).append(flag)
            self.ws.save_artifact(element_id, self.st(element_id).version, artifact)
        self.st(element_id).feedback = []
        if by == "human":   # решение человека закрывает и контрольную точку элемента
            return self._approve(element_id, {"by": "human", "at": now()})
        return self._after_pass(element_id, artifact)

    def _approve(self, element_id: str, decision: dict) -> Action:
        element = self.reg.element(element_id)
        st = self.st(element_id)
        if element.on_approve:
            artifact = element.on_approve(self.ws.load_artifact(element_id) or {},
                                          {**decision, "low_confidence": self.low_confidence_decisions()})
            artifact = element.output.model_validate(artifact).model_dump(mode="json")
            self.ws.save_artifact(element_id, st.version, artifact)
        self._set(element_id, "done", checkpoint="")
        self.state.log("approved", element_id, by=decision.get("by", ""))
        self.save()
        return Action("done", element_id)

    def _rerun(self, element_id: str, comment: str) -> Action:
        self._invalidate([element_id] + self.reg.downstream(element_id))
        self._set(element_id, "pending", feedback=[FeedbackItem(problem=comment, target=element_id).model_dump()])
        self.state.log("rerun", element_id, comment=comment)
        self.save()
        return Action("looped", element_id, {"targets": [element_id], "summary": comment})

    def _arbiter(self, element: Element, artifact: dict) -> CheckpointDecision:
        if self.config.arbiter == "executor" and self.factory is not None:
            try:
                prompt = self.checkpoints.arbiter_prompt(element, artifact, element.instructions.auto_note)
                rel = f"tasks/arbiter.{element.id}.v{self.st(element.id).version}.md"
                self.ws.write_text(rel, prompt)
                name = self.config.executor_for("hitl")
                result = self.factory(name).execute(Task(
                    element_id=element.id, title="Арбитр", workspace=self.ws.root, task_file=self.ws.path(rel),
                    schema=ArbiterVerdict.model_json_schema(), schema_file=self.ws.path(rel), prompt=prompt,
                    result_file=self.ws.path(f"results/arbiter.{element.id}.json"), kind="arbiter",
                    model=self.config.model_for("hitl", name), log_file=self.ws.path(f"logs/arbiter.{element.id}.log")))
                verdict = ArbiterVerdict.model_validate(result.data or {})
                self.st(element.id).cost_usd += result.cost_usd
                return CheckpointDecision(
                    element_id=element.id, decision=verdict.decision, by="arbiter", confidence=verdict.confidence,
                    low_confidence=verdict.confidence < self.config.arbiter_min_confidence,
                    comment=verdict.rationale, at=now())
            except (ExecutorError, ValidationError) as exc:
                self.state.log("arbiter_fallback", element.id, error=str(exc)[:300])
        return self.checkpoints.rules_decision(element, artifact)

    def _update_trace(self) -> None:
        artifacts = {e.id: self.ws.load_artifact(e.id) for e in self.reg.stages if self.st(e.id).version}
        self.ws.write_json("output/trace.json", build_graph(artifacts).model_dump())

    def low_confidence_decisions(self) -> list[str]:
        result = []
        for d in self.ws.decisions():
            if d.get("low_confidence"):
                element = self.reg.elements.get(d["element_id"])
                name = f"{element.num} {element.title}" if element else d["element_id"]
                result.append(f"{name}: {d.get('comment', '')} (уверенность {d.get('confidence')})")
        return result

    # ================================================================== решения людей

    def approve(self, element_id: str, comment: str = "", by: str = "human") -> Action:
        with self._lock:
            st = self.st(element_id)
            if st.status != "awaiting_approval":
                raise StateError(f"{element_id}: решение не ожидается (статус {st.status})")
            decision = CheckpointDecision(element_id=element_id, kind=st.checkpoint or "approval", decision="approve",
                                          by=by, comment=comment, at=now())
            self.checkpoints.record(decision)
            if st.checkpoint == "loop_budget":
                return self._accept_with_risk(element_id, st.feedback, by=by)
            return self._approve(element_id, decision.model_dump())

    def reject(self, element_id: str, comment: str, by: str = "human") -> Action:
        with self._lock:
            st = self.st(element_id)
            if st.status != "awaiting_approval":
                raise StateError(f"{element_id}: решение не ожидается (статус {st.status})")
            self.checkpoints.record(CheckpointDecision(element_id=element_id, kind=st.checkpoint or "approval",
                                                       decision="reject", by=by, comment=comment, at=now()))
            if st.checkpoint == "loop_budget":
                # ещё одна итерация: вернуть замечания адресатам, расширив бюджет
                element = self.reg.element(element_id)
                items = [FeedbackItem.model_validate(f) for f in st.feedback]
                for target in {i.target for i in items}:
                    key = f"{element_id}->{target}"
                    self.state.loop_counts[key] = max(0, self.state.loop_counts.get(key, 1) - 1)
                outcome = GateOutcome(passed=False, feedback={}, summary=comment)
                for i in items:
                    outcome.feedback.setdefault(i.target or element.default_loop_target(), []).append(i)
                return self._handle_failure(element_id, outcome)
            return self._rerun(element_id, comment)

    def rerun(self, element_id: str, comment: str) -> Action:
        """Вернуть любой выполненный элемент на доработку с комментарием."""
        with self._lock:
            self.reg.element(element_id)
            return self._rerun(element_id, comment)

    # ================================================================== следующее действие

    def advance_deterministic(self) -> list[str]:
        """Выполнить все готовые детерминированные элементы (вход, сборка SRS)."""
        done = []
        progressed = True
        while progressed:
            progressed = False
            for element in self.reg.stages:
                if element.mode == "deterministic" and self.is_ready(element.id):
                    with self._lock:
                        self.st(element.id).runs += 1
                        self._set(element.id, "in_progress")
                        data = element.run(self.context(element.id))
                        self._complete(element.id, data)
                    done.append(element.id)
                    progressed = True
        return done

    def _task_action(self, element_id: str) -> Action:
        element = self.reg.element(element_id)
        st = self.st(element_id)
        result = self.ws.path(st.result_file)
        return Action("task", element_id, {
            "num": element.num, "title": element.title, "domain": element.domain, "gate": element.gate or "",
            "task_file": str(self.ws.path(st.task_file)), "schema_file": str(self.ws.path(st.schema_file)),
            "result_file": str(result), "capabilities": sorted(element.capabilities),
            "iteration": st.version, "feedback": len(st.feedback), "autonomous": self.config.autonomous,
            "submit": f'reqpipe submit {element_id} "{result}" -w "{self.ws.root}"',
        })

    def _approval_action(self, element_id: str) -> Action:
        element = self.reg.element(element_id)
        st = self.st(element_id)
        artifact = self.ws.load_artifact(element_id) or {}
        w = f' -w "{self.ws.root}"'
        if st.checkpoint == "loop_budget":
            question = (f"Бюджет возвратов фильтра {element.gate or element.num} исчерпан. Принять результат с "
                        f"замечаниями как риск (approve) или дать ещё одну итерацию (reject)?")
            details = "\n".join(f"• {f.get('problem', '')}" for f in st.feedback)
        else:
            question = f"Утвердить результат этапа {element.num} «{element.title}»?"
            details = summarize(artifact)
            open_questions = artifact.get("open_questions") or []
            if open_questions:
                question += (" Есть открытые вопросы к автору: ответьте на них, вернув этап на доработку "
                             "(комментарий = ответы), или утвердите как есть.")
                details += "\n\nОткрытые вопросы:\n" + "\n".join(f"  {n}. {q}" for n, q in enumerate(open_questions, 1))
        return Action("approval", element_id, {
            "num": element.num, "title": element.title, "checkpoint": st.checkpoint or "approval",
            "question": question, "summary": details, "hitl": element.instructions.hitl,
            "artifact_file": str(self.ws.path(f"artifacts/{element_id}.json")),
            "approve": f"reqpipe approve {element_id}{w}",
            "reject": f'reqpipe reject {element_id} --comment "<что исправить>"{w}',
        })

    def _external_action(self, element_id: str) -> Action:
        element = self.reg.element(element_id)
        plan = self.st(element_id).plan or {}
        self.ws.write_json(f"results/{element_id}.plan.json", plan)
        w = f' -w "{self.ws.root}"'
        return Action("external", element_id, {
            "num": element.num, "title": element.title,
            "plan_file": str(self.ws.path(f"results/{element_id}.plan.json")),
            "prototype": str(self.ws.path(plan.get("_prototype_path", ""))) if plan.get("_prototype_path") else "",
            "results_schema": element.external_model.model_json_schema() if element.external_model else {},
            "submit": f'reqpipe submit-external {element_id} "<results.json>"{w}',
            "waive": f'reqpipe waive {element_id} --reason "<почему пропускаем>"{w}',
        })

    def next_action(self) -> Action:
        """Следующее действие для агента/человека; детерминированные этапы выполняются сами."""
        if self.state.stopped:
            return Action("stopped", data={"reason": self.state.stopped})
        self.advance_deterministic()
        if self.is_complete():
            return self._complete_action()
        for status, make in (("awaiting_approval", self._approval_action),
                             ("awaiting_external", self._external_action)):
            eid = self.first(status)
            if eid:
                if status == "awaiting_external" and self.config.user_test_command:
                    action = self._run_external_command(eid)
                    if action.kind != "external":
                        return self.next_action()
                return make(eid)
        failed = self.first("failed")
        if failed:
            return Action("failed", failed, {"error": self.st(failed).last_error})
        busy = self.first("in_progress")
        if busy:
            return self._task_action(busy)
        ready = next((e.id for e in self.reg.stages if e.mode in ("agent", "external") and self.is_ready(e.id)), None)
        if ready:
            self.prepare(ready)
            return self._task_action(ready)
        return Action("blocked", data={"reason": "Нет готовых этапов — проверьте `reqpipe status`"})

    def _complete_action(self) -> Action:
        srs = self.ws.load_artifact("srs") or {}
        return Action("complete", "srs", {
            "files": {k: str(self.ws.path(v)) for k, v in srs.get("files", {}).items()},
            "flags": srs.get("flags", []), "cost_usd": self.state.total_cost,
        })

    def _run_external_command(self, element_id: str) -> Action:
        plan_rel = f"results/{element_id}.plan.json"
        out_rel = f"results/{element_id}.results.json"
        self.ws.write_json(plan_rel, self.st(element_id).plan or {})
        cmd = self.config.user_test_command.format(plan=self.ws.path(plan_rel), out=self.ws.path(out_rel))
        proc = subprocess.run(shlex.split(cmd, posix=False), cwd=self.ws.root, capture_output=True, text=True,
                              encoding="utf-8", errors="replace")
        if proc.returncode != 0 or not self.ws.path(out_rel).exists():
            self.state.log("external_command_failed", element_id, stderr=proc.stderr[-500:])
            self.save()
            return self._external_action(element_id)
        return self.submit_external(element_id, self.ws.read_json(out_rel), by="command")

    # ================================================================== автономный прогон

    def run(self, max_steps: int | None = None, approver: Approver | None = None,
            until: str | None = None, on_event: Callable[[str], None] | None = None) -> RunReport:
        """Вести конвейер, вызывая агентов-исполнителей, пока есть работа."""
        if self.factory is None:
            raise StateError("Не задан исполнитель для автоматического прогона")
        report = RunReport()
        say = on_event or (lambda _msg: None)
        steps = 0
        while True:
            if self.state.stopped:
                report.stop = Action("stopped", data={"reason": self.state.stopped})
                break
            for eid in self.advance_deterministic():
                say(f"✓ {self._label(eid)} — выполнен автоматически")
                report.steps.append(eid)
            if until and self.st(until).status == "done":
                report.stop = Action("done", until)
                break
            if self.is_complete():
                report.stop = self._complete_action()
                break
            approval = self.first("awaiting_approval")
            if approval:
                action = self._approval_action(approval)
                if approver is None:
                    report.stop = action
                    break
                verdict, comment = approver(action)
                if verdict == "approve":
                    self.approve(approval, comment)
                elif verdict == "reject":
                    self.reject(approval, comment or "Вернуть на доработку")
                else:
                    report.stop = action
                    break
                continue
            external = self.first("awaiting_external")
            if external:
                action = self._handle_external_in_run(external)
                if action.kind == "external":
                    report.stop = action
                    break
                continue
            failed = self.first("failed")
            if failed:
                report.stop = Action("failed", failed, {"error": self.st(failed).last_error})
                break
            ready = [e.id for e in self.reg.stages if e.mode in ("agent", "external")
                     and (self.is_ready(e.id) or self.st(e.id).status == "in_progress")]
            if not ready:
                report.stop = Action("blocked", data={"reason": "Нет готовых этапов"})
                break
            if max_steps is not None and steps >= max_steps:
                report.stop = Action("paused", data={"reason": f"Достигнут лимит шагов: {max_steps}"})
                break
            batch = ready[: max(1, self.config.parallel)]
            manual = [e for e in batch if self.config.executor_for(e) == "manual"]
            if manual:
                report.stop = Action("manual", manual[0], {"reason": "Этап назначен ручному исполнителю (manual): "
                                                                    "выполните его через `reqpipe next`/`submit`"})
                break
            for eid in batch:
                say(f"→ {self._label(eid)} — {self.config.executor_for(eid)}")
            if len(batch) == 1:
                outcomes = [self._execute(batch[0])]
            else:
                with ThreadPoolExecutor(max_workers=len(batch)) as pool:
                    outcomes = list(pool.map(self._execute, batch))
            for eid, action in zip(batch, outcomes):
                steps += 1
                report.steps.append(eid)
                say(self._describe(eid, action))
        report.cost_usd = self.state.total_cost
        return report

    def _execute(self, element_id: str) -> Action:
        """Выполнить этап агентом с попытками исправить ответ, не прошедший контракт."""
        name = self.config.executor_for(element_id)
        executor = self.factory(name)
        errors: list[str] | None = None
        for _attempt in range(self.config.max_repairs + 1):
            task = self.prepare(element_id, repair_errors=errors)
            try:
                result = executor.execute(task)
            except ExecutorError as exc:
                with self._lock:
                    self._set(element_id, "failed", last_error=str(exc))
                    self.save()
                return Action("failed", element_id, {"error": str(exc)})
            if result.data is None:
                errors = ["ответ не содержит JSON-объекта"]
                with self._lock:
                    st = self.st(element_id)
                    st.repairs += 1
                    st.cost_usd += result.cost_usd
                    self.save()
                continue
            try:
                return self.submit(element_id, result.data, cost=result.cost_usd)
            except ContractViolation as exc:
                errors = exc.errors
        with self._lock:
            self._set(element_id, "failed", last_error="Ответ агента не прошёл контракт: " + "; ".join(errors or [])[:1500])
            self.save()
        return Action("failed", element_id, {"error": self.st(element_id).last_error})

    def _handle_external_in_run(self, element_id: str) -> Action:
        element = self.reg.element(element_id)
        if self.config.user_test_command:
            return self._run_external_command(element_id)
        if self.config.executor_for(element_id) == "mock" and element.example_results:
            results = element.example_results(self.context(element_id), self.st(element_id).plan or {})
            return self.submit_external(element_id, results, by="mock")
        if self.config.autonomous and self.config.allow_waive_user_test:
            return self.waive(element_id, "Автономный режим без сервиса тестирования: этап пропущен арбитром",
                              by="arbiter")
        return self._external_action(element_id)

    def _label(self, element_id: str) -> str:
        e = self.reg.element(element_id)
        return f"{e.num} {e.title}"

    def _describe(self, element_id: str, action: Action) -> str:
        label = self._label(element_id)
        if action.kind == "done":
            return f"✓ {label}"
        if action.kind == "looped":
            targets = ", ".join(self._label(t) for t in action.data.get("targets", []))
            return f"↺ {label}: возврат на доработку → {targets}"
        if action.kind == "approval":
            return f"? {label}: ждёт решения на контрольной точке"
        if action.kind == "external":
            return f"⏸ {label}: ждёт результатов теста с пользователями"
        if action.kind == "failed":
            return f"✗ {label}: {action.data.get('error', '')[:300]}"
        if action.kind == "stopped":
            return f"■ {label}: конвейер остановлен — {action.data.get('reason', '')}"
        return f"· {label}: {action.kind}"


ELEMENT = Element(
    id="orch", num="", title="Оркестратор процесса", actor="Агент-координатор", kind="agent", mode="service",
    instructions=Instructions(
        purpose=(
            "Управляет всем конвейером как графом состояний. Именно он превращает набор отдельных агентов в "
            "согласованный процесс с итерациями."
        ),
        methods=(
            "Параллельный запуск независимых агентов фазы 2",
            "Маршрутизация по результатам quality gates: дальше или на доработку",
            "Бюджет итераций и защита от бесконечных циклов",
            "Передача каждому агенту только нужного контекста — через менеджер контекста на каждом переходе между фазами",
        ),
        prompt=(
            "Перед переходом к следующей фазе убедись, что выполнены критерии готовности текущей. Если проверка не "
            "пройдена после трёх итераций — эскалируй человеку."
        ),
        done="Все фазы завершены, критерии готовности выполнены, открытых эскалаций нет.",
        auto_note=(
            "Эскалации уходят не человеку, а агенту-арбитру; при исчерпании бюджета итераций прогон останавливается "
            "с отчётом."
        ),
    ),
)
