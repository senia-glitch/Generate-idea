"""Командная строка ``reqpipe``.

Два способа работы:
* агент ведёт конвейер (executor = manual): ``reqpipe next`` → выполнить задачу →
  ``reqpipe submit``; так работают скиллы для Claude Code и OpenCode;
* пакет ведёт агентов: ``reqpipe run`` сам вызывает ``claude -p`` / ``opencode run``.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from importlib import resources
from pathlib import Path

from reqpipe import __version__
from reqpipe.catalog import build_registry
from reqpipe.core.config import EXECUTORS, RunConfig
from reqpipe.core.errors import ContractViolation, ReqpipeError
from reqpipe.domains.platform.knowledge_base import Workspace
from reqpipe.domains.platform.orchestrator import Action, Engine
from reqpipe.executors import make_executor

DEFAULT_WS = ".reqpipe"
ICONS = {"done": "✓", "pending": "·", "in_progress": "→", "awaiting_approval": "?", "awaiting_external": "⏸",
         "failed": "✗"}
STATUS_RU = {"done": "готово", "pending": "ждёт", "in_progress": "в работе", "awaiting_approval": "ждёт решения",
             "awaiting_external": "ждёт результатов", "failed": "ошибка"}


# ------------------------------------------------------------------------------------------- утилиты

def reqpipe_command(absolute: bool = False) -> str:
    """Как вызвать именно эту установку reqpipe из другой оболочки (например, из агента).

    Если в PATH есть ``reqpipe`` из того же окружения — просто ``reqpipe``; иначе (пакет в отдельном
    виртуальном окружении, которое не активировано) — полный путь к python этого окружения.
    """
    python = Path(sys.executable)
    found = shutil.which("reqpipe")
    if not absolute and found and Path(found).resolve().parent == python.resolve().parent:
        return "reqpipe"
    return f'"{python.as_posix()}" -m reqpipe'


def skill_dirs(global_: bool, dest: Path) -> dict[str, Path]:
    """Куда класть скиллы: в проект или в профиль пользователя (видны в любой папке)."""
    if global_:
        home = Path.home()
        return {"claude": home / ".claude" / "skills", "opencode": home / ".config" / "opencode" / "skills"}
    return {"claude": dest / ".claude" / "skills", "opencode": dest / ".opencode" / "skills"}


def _ws(args) -> Workspace:
    return Workspace(args.workspace or os.environ.get("REQPIPE_WORKSPACE") or DEFAULT_WS)


def _engine(args, require: bool = True) -> Engine:
    ws = _ws(args)
    if require and not ws.exists():
        raise ReqpipeError(f"Рабочая область не найдена: {ws.root}. Создайте её: reqpipe init --idea idea.md")
    engine = Engine(build_registry(), ws)
    engine.factory = lambda name: make_executor(name, engine.config)
    engine.command = reqpipe_command()
    return engine


def _read_payload(source: str) -> str:
    if source == "-":
        return sys.stdin.read()
    return Path(source).read_text(encoding="utf-8")


def _print_action(action: Action, as_json: bool) -> None:
    if as_json:
        print(json.dumps(action.to_dict(), ensure_ascii=False, indent=2))
        return
    d = action.data
    if action.kind == "task":
        print(f"→ Задача: {d['num']} «{d['title']}»" + (f" · фильтр {d['gate']}" if d.get("gate") else ""))
        if d.get("feedback"):
            print(f"  доработка: {d['feedback']} замечаний, итерация {d['iteration'] + 1}")
        print(f"  задача:    {d['task_file']}")
        print(f"  схема:     {d['schema_file']}")
        print(f"  результат: {d['result_file']}")
        print(f"  сдать:     {d['submit']}")
    elif action.kind == "approval":
        print(f"? {d['question']}")
        if d.get("hitl"):
            print(f"  роль человека: {d['hitl']}")
        print(d.get("summary", ""))
        print(f"  артефакт: {d['artifact_file']}")
        print(f"  утвердить: {d['approve']}\n  вернуть:   {d['reject']}")
    elif action.kind == "external":
        print(f"⏸ {d['num']} «{d['title']}»: нужны результаты теста с пользователями")
        if d.get("prototype"):
            print(f"  прототип: {d['prototype']}")
        print(f"  план:     {d['plan_file']}")
        print(f"  сдать:    {d['submit']}\n  пропустить (с пометкой в спецификации): {d['waive']}")
    elif action.kind == "complete":
        print("✓ Конвейер завершён. Спецификация:")
        for name, path in d.get("files", {}).items():
            print(f"  {name}: {path}")
        for flag in d.get("flags", []):
            print(f"  ⚠ {flag}")
        if d.get("cost_usd"):
            print(f"  стоимость вызовов агентов: ${d['cost_usd']}")
    elif action.kind in ("failed", "stopped", "blocked", "manual", "paused"):
        mark = {"failed": "✗", "stopped": "■", "blocked": "·", "manual": "✋", "paused": "⏸"}[action.kind]
        print(f"{mark} {action.element or ''} {d.get('error') or d.get('reason') or ''}".strip())
    elif action.kind == "looped":
        print(f"↺ {action.element}: возврат на доработку → {', '.join(d.get('targets', []))}")
    elif action.kind == "done":
        print(f"✓ {action.element}: принято")
    else:
        print(json.dumps(action.to_dict(), ensure_ascii=False))


# ------------------------------------------------------------------------------------------- команды

def cmd_init(args) -> int:
    if args.idea:
        idea = Path(args.idea).read_text(encoding="utf-8")
    elif args.idea_text:
        idea = args.idea_text
    else:
        raise ReqpipeError("Нужна идея: --idea файл.md или --idea-text \"…\"")
    config = RunConfig(executor=args.executor, autonomous=args.autonomous, parallel=args.parallel)
    ws = _ws(args)
    ws.init(idea, config, force=args.force)
    print(f"✓ Рабочая область: {ws.root}")
    print(f"  исполнитель: {config.executor} · автономный режим: {'да' if config.autonomous else 'нет'}")
    print(f"  настройки: {ws.path(Workspace.CONFIG)}")
    cmd = reqpipe_command()
    print(f"  дальше: {cmd} next   (агент ведёт конвейер)  или  {cmd} run --executor claude-code|opencode|mock")
    return 0


def cmd_status(args) -> int:
    engine = _engine(args)
    if args.json:
        data = {e.id: {"num": e.num, "domain": e.domain, "status": engine.st(e.id).status,
                       "version": engine.st(e.id).version, "cost_usd": engine.st(e.id).cost_usd}
                for e in engine.reg.stages}
        print(json.dumps({"elements": data, "loops": engine.state.loop_counts, "flags": engine.state.flags,
                          "stopped": engine.state.stopped, "cost_usd": engine.state.total_cost},
                         ensure_ascii=False, indent=2))
        return 0
    cfg = engine.config
    print(f"Рабочая область {engine.ws.root} · исполнитель {cfg.executor} · "
          f"{'автономный режим' if cfg.autonomous else 'человек в контуре'}")
    for domain in engine.reg.domains.values():
        if domain.service:
            continue
        print(f"\n{domain.name}")
        for e in domain.elements:
            st = engine.st(e.id)
            extra = f" v{st.version}" if st.version else ""
            gate = f" [{e.gate}]" if e.gate else ""
            ex = cfg.executor_for(e.id) if e.mode in ("agent", "external") else "авто"
            print(f"  {ICONS.get(st.status, '?')} {e.num:>4} {e.title}{gate} — {STATUS_RU.get(st.status, st.status)}{extra}"
                  f"  ({ex})")
    if engine.state.loop_counts:
        print("\nВозвраты: " + ", ".join(f"{k} ×{v}" for k, v in engine.state.loop_counts.items()))
    for flag in engine.state.flags:
        print(f"⚠ {flag}")
    if engine.state.stopped:
        print(f"■ Остановлен: {engine.state.stopped}")
    if engine.state.total_cost:
        print(f"Стоимость вызовов агентов: ${engine.state.total_cost}")
    return 0


def cmd_next(args) -> int:
    _print_action(_engine(args).next_action(), args.json)
    return 0


def cmd_submit(args) -> int:
    engine = _engine(args)
    try:
        action = engine.submit(args.element, _read_payload(args.file))
    except ContractViolation as exc:
        print(f"✗ Ответ не прошёл контракт {args.element}. Исправьте и отправьте снова:", file=sys.stderr)
        for err in exc.errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        return 2
    _print_action(action, args.json)
    return 0


def cmd_submit_external(args) -> int:
    engine = _engine(args)
    try:
        action = engine.submit_external(args.element, _read_payload(args.file))
    except ContractViolation as exc:
        print("✗ Результаты не прошли контракт:", file=sys.stderr)
        for err in exc.errors[:50]:
            print(f"  - {err}", file=sys.stderr)
        return 2
    _print_action(action, args.json)
    return 0


def cmd_approve(args) -> int:
    _print_action(_engine(args).approve(args.element, args.comment or ""), args.json)
    return 0


def cmd_reject(args) -> int:
    _print_action(_engine(args).reject(args.element, args.comment), args.json)
    return 0


def cmd_waive(args) -> int:
    _print_action(_engine(args).waive(args.element, args.reason), args.json)
    return 0


def cmd_rerun(args) -> int:
    _print_action(_engine(args).rerun(args.element, args.comment), args.json)
    return 0


def _interactive_approver(action: Action) -> tuple[str, str]:
    if not sys.stdin.isatty():
        return ("quit", "")
    print()
    _print_action(action, False)
    while True:
        answer = input("[y] утвердить · [n] вернуть с комментарием · [q] остановиться: ").strip().lower()
        if answer in ("y", "д", "yes", "да"):
            return ("approve", "")
        if answer in ("n", "н", "no", "нет"):
            return ("reject", input("Что исправить: ").strip())
        if answer in ("q", "й", "quit"):
            return ("quit", "")


def cmd_run(args) -> int:
    engine = _engine(args)
    if args.executor:
        engine.config.executor = args.executor
    if args.parallel:
        engine.config.parallel = args.parallel
    approver = None if args.no_input else _interactive_approver
    report = engine.run(max_steps=args.max_steps, approver=approver, until=args.until, on_event=print)
    if report.stop:
        print()
        _print_action(report.stop, args.json)
    kind = report.stop.kind if report.stop else ""
    if kind in ("complete", "done", "paused"):
        return 0
    return 3 if kind in ("approval", "external", "manual") else 1   # 3 — ждём человека, 1 — ошибка/остановка


def cmd_autonomy(args) -> int:
    ws = _ws(args)
    config = ws.load_config()
    config.autonomous = args.mode == "on"
    ws.save_config(config)
    print("Автономный режим " + ("включён: решения на контрольных точках принимает агент-арбитр"
                                 if config.autonomous else "выключен: решения принимает человек"))
    return 0


def cmd_spec(args) -> int:
    reg = build_registry()
    if args.json:
        print(json.dumps({
            "domains": {d.id: {"phase": d.phase, "name": d.name, "elements": [e.id for e in d.elements]}
                        for d in reg.domains.values()},
            "contracts": [{"source": c.source, "target": c.target, "artifact": c.model.__name__,
                           "fields": list(c.fields), "note": c.note} for c in reg.contracts],
            "loops": [{"source": s, "target": l.target, "label": l.label, "in_reference": l.in_reference}
                      for s, l in reg.loops],
        }, ensure_ascii=False, indent=2))
        return 0
    for d in reg.domains.values():
        print(f"\n[{d.phase}] {d.name}  (reqpipe.domains.{d.id})")
        for e in d.elements:
            gate = f" [{e.gate}]" if e.gate else ""
            out = e.output.__name__ if e.output else "—"
            print(f"  {e.num or '·':>4} {e.id:<12} {e.title}{gate}  → {out}")
            for c in reg.incoming(e.id):
                fields = f" {{{', '.join(c.fields)}}}" if c.fields else ""
                print(f"         ← {c.source}: {c.model.__name__}{fields}")
            for l in e.loops:
                print(f"         ↺ {l.target}: {l.label}" + ("" if l.in_reference else "  (уточнение)"))
    return 0


def cmd_schema(args) -> int:
    element = build_registry().element(args.element)
    model = element.external_model if args.external else element.response_model
    if model is None:
        raise ReqpipeError(f"{args.element}: у элемента нет такой схемы")
    print(json.dumps(model.model_json_schema(), ensure_ascii=False, indent=2))
    return 0


def cmd_check_reference(args) -> int:
    from reqpipe.reference import check, find_reference
    path = Path(args.html) if args.html else find_reference()
    if path is None or not path.exists():
        raise ReqpipeError("Эталон requirements-pipeline.html не найден; укажите путь: --html")
    report = check(build_registry(), path)
    print(f"Эталон: {path}")
    for err in report.errors:
        print(f"  ✗ {err}")
    for note in report.notes:
        print(f"  · {note}")
    print("✓ Система соответствует эталонной схеме" if report.ok else "✗ Есть расхождения с эталоном")
    return 0 if report.ok else 1


def cmd_install_skills(args) -> int:
    targets = skill_dirs(args.global_, Path(args.dest).resolve())
    command = reqpipe_command(absolute=True)
    root = resources.files("reqpipe") / "skills"
    for agent in args.agents.split(","):
        agent = agent.strip()
        if agent not in targets:
            raise ReqpipeError(f"Неизвестный агент {agent!r}: допустимо claude, opencode")
        for skill in sorted((root / agent).iterdir(), key=lambda p: p.name):
            if not skill.is_dir():
                continue
            target = targets[agent] / skill.name
            target.mkdir(parents=True, exist_ok=True)
            text = (skill / "SKILL.md").read_text(encoding="utf-8").replace("{{REQPIPE}}", command)
            (target / "SKILL.md").write_text(text, encoding="utf-8")
            print(f"✓ {agent}: {target / 'SKILL.md'}")
    print(f"  в скиллы записан вызов этой установки: {command}")
    print("  перезапустите агента, если он уже открыт")
    return 0


def cmd_doctor(args) -> int:
    print(f"reqpipe {__version__} · Python {sys.version.split()[0]} · {Path(sys.executable).parent}")
    print(f"  вызов этой установки: {reqpipe_command()}")
    for name in ("claude", "opencode"):
        path = shutil.which(name)
        print(f"  {'✓' if path else '✗'} агент {name}: {path or 'не найден в PATH'}")
    for scope, dirs in (("глобально", skill_dirs(True, Path.cwd())), ("в этой папке", skill_dirs(False, Path.cwd()))):
        for agent, folder in dirs.items():
            ok = (folder / "reqpipe-pipeline" / "SKILL.md").exists()
            if ok or scope == "глобально":
                print(f"  {'✓' if ok else '·'} скиллы для {agent} {scope}: {folder}" + ("" if ok else " — не установлены"))
    ws = _ws(args)
    print(f"  {'✓' if ws.exists() else '·'} рабочая область {ws.root}" + ("" if ws.exists() else " — не создана"))
    from reqpipe.reference import check, find_reference
    ref = find_reference()
    if ref:
        report = check(build_registry(), ref)
        print(f"  {'✓' if report.ok else '✗'} эталон {ref}: " + ("соответствует" if report.ok else
                                                                f"расхождений {len(report.errors)}"))
    return 0


# ------------------------------------------------------------------------------------------- разбор аргументов

def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-w", "--workspace", help=f"рабочая область прогона (по умолчанию {DEFAULT_WS} "
                                                  "или $REQPIPE_WORKSPACE)")
    common.add_argument("--json", action="store_true", help="вывод в JSON (для агентов)")

    p = argparse.ArgumentParser(prog="reqpipe", description="Конвейер «сырая идея → функциональные требования»")
    p.add_argument("--version", action="version", version=f"reqpipe {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    s = sub.add_parser("init", parents=[common], help="создать рабочую область прогона")
    s.add_argument("--idea", help="файл с идеей")
    s.add_argument("--idea-text", help="текст идеи")
    s.add_argument("--executor", choices=EXECUTORS, default="manual")
    s.add_argument("--autonomous", action="store_true", help="решения на контрольных точках — агент-арбитр")
    s.add_argument("--parallel", type=int, default=1)
    s.add_argument("--force", action="store_true", help="перезаписать существующую область")
    s.set_defaults(func=cmd_init)

    sub.add_parser("status", parents=[common], help="состояние этапов").set_defaults(func=cmd_status)
    sub.add_parser("next", parents=[common], help="следующее действие (задача, решение, внешний этап)") \
        .set_defaults(func=cmd_next)

    s = sub.add_parser("submit", parents=[common], help="сдать результат этапа (JSON)")
    s.add_argument("element")
    s.add_argument("file", help="файл с JSON или «-» для stdin")
    s.set_defaults(func=cmd_submit)

    s = sub.add_parser("submit-external", parents=[common], help="сдать результаты теста с пользователями")
    s.add_argument("element")
    s.add_argument("file")
    s.set_defaults(func=cmd_submit_external)

    s = sub.add_parser("approve", parents=[common], help="утвердить результат на контрольной точке")
    s.add_argument("element")
    s.add_argument("--comment", default="")
    s.set_defaults(func=cmd_approve)

    s = sub.add_parser("reject", parents=[common], help="вернуть результат на доработку")
    s.add_argument("element")
    s.add_argument("--comment", required=True)
    s.set_defaults(func=cmd_reject)

    s = sub.add_parser("waive", parents=[common], help="явно пропустить внешний этап (помечается в SRS)")
    s.add_argument("element")
    s.add_argument("--reason", required=True)
    s.set_defaults(func=cmd_waive)

    s = sub.add_parser("rerun", parents=[common], help="вернуть любой этап на доработку")
    s.add_argument("element")
    s.add_argument("--comment", required=True)
    s.set_defaults(func=cmd_rerun)

    s = sub.add_parser("run", parents=[common], help="вести конвейер автоматически через агентов")
    s.add_argument("--executor", choices=[e for e in EXECUTORS if e != "manual"])
    s.add_argument("--parallel", type=int)
    s.add_argument("--max-steps", type=int)
    s.add_argument("--until", help="остановиться после этого элемента")
    s.add_argument("--no-input", action="store_true", help="не спрашивать решения в терминале — остановиться")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("autonomy", parents=[common], help="включить/выключить автономный режим")
    s.add_argument("mode", choices=["on", "off"])
    s.set_defaults(func=cmd_autonomy)

    sub.add_parser("spec", parents=[common], help="домены, элементы, контракты и петли").set_defaults(func=cmd_spec)

    s = sub.add_parser("schema", parents=[common], help="JSON-схема ответа элемента")
    s.add_argument("element")
    s.add_argument("--external", action="store_true", help="схема внешних результатов")
    s.set_defaults(func=cmd_schema)

    s = sub.add_parser("check-reference", parents=[common], help="сверить систему с эталонной схемой HTML")
    s.add_argument("--html", help="путь к requirements-pipeline.html")
    s.set_defaults(func=cmd_check_reference)

    s = sub.add_parser("install-skills", parents=[common], help="установить скиллы для Claude Code и OpenCode")
    s.add_argument("--global", dest="global_", action="store_true",
                   help="в профиль пользователя (~/.claude/skills, ~/.config/opencode/skills) — видны в любой папке")
    s.add_argument("--dest", default=".", help="папка проекта (если не --global)")
    s.add_argument("--agents", default="claude,opencode")
    s.set_defaults(func=cmd_install_skills)

    sub.add_parser("doctor", parents=[common], help="проверить окружение").set_defaults(func=cmd_doctor)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (ReqpipeError, FileExistsError, FileNotFoundError, KeyError, json.JSONDecodeError) as exc:
        print(f"✗ {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
