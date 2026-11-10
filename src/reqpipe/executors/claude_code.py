"""Исполнитель Claude Code: ``claude -p`` в неинтерактивном режиме.

Каждый этап — отдельная сессия без сохранения (``--no-session-persistence``):
агент видит только пакет контекста своего этапа. Ответ проверяется по
JSON-схеме контракта (``--json-schema``) и возвращается в ``structured_output``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime

from reqpipe.core.config import ExecutorConfig
from reqpipe.core.errors import ExecutorError
from reqpipe.executors.base import ExecutionResult, Task, extract_json, inline_refs

BASE_TOOLS = ("Read", "Glob", "Grep")
WEB_TOOLS = ("WebSearch", "WebFetch")
MAX_SCHEMA_ARG = 24_000   # длиннее — схема остаётся только в тексте задачи (ограничение командной строки Windows)


def build_argv(command: str, task: Task) -> list[str]:
    tools = list(BASE_TOOLS) + (list(WEB_TOOLS) if "web" in task.capabilities else [])
    prompt = (f"Прочитай файл задачи {task.task_file} (UTF-8) и выполни её полностью. "
              "Итоговый ответ — только JSON по схеме из задачи, без пояснений.")
    argv = [command, "-p", prompt, "--output-format", "json", "--no-session-persistence",
            "--allowedTools", ",".join(tools)]
    schema = json.dumps(inline_refs(task.schema), ensure_ascii=False)
    if len(schema) <= MAX_SCHEMA_ARG:
        argv += ["--json-schema", schema]
    if task.model:
        argv += ["--model", task.model]
    return argv + list(task.extra_args)


def parse_output(stdout: str) -> ExecutionResult:
    envelope = None
    for line in reversed([l for l in stdout.splitlines() if l.strip()]):
        try:
            envelope = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    if envelope is None:
        envelope = extract_json(stdout)
    if not isinstance(envelope, dict):
        raise ExecutorError("Claude Code вернул ответ не в формате JSON")
    if envelope.get("is_error"):
        raise ExecutorError(f"Claude Code завершился с ошибкой: {envelope.get('result') or envelope.get('subtype')}")
    data = envelope.get("structured_output")
    if not isinstance(data, dict):
        data = extract_json(envelope.get("result", ""))
    return ExecutionResult(data=data, raw=stdout, cost_usd=float(envelope.get("total_cost_usd") or 0.0))


class ClaudeCodeExecutor:
    name = "claude-code"

    def __init__(self, config: ExecutorConfig | None):
        self.config = config or ExecutorConfig(command="claude")

    def execute(self, task: Task) -> ExecutionResult:
        command = shutil.which(self.config.command or "claude")
        if not command:
            raise ExecutorError("Не найдена команда Claude Code (`claude`). Установите Claude Code или укажите путь "
                                "в [executor.\"claude-code\"] command.")
        argv = build_argv(command, task)
        try:
            proc = subprocess.run(argv, cwd=task.workspace, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=task.timeout_sec, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired as exc:
            raise ExecutorError(f"Claude Code не уложился в {task.timeout_sec} с") from exc
        if task.log_file:
            task.log_file.parent.mkdir(parents=True, exist_ok=True)
            task.log_file.write_text(
                f"# {datetime.now().isoformat()} exit={proc.returncode}\n{proc.stdout}\n--- stderr ---\n{proc.stderr}",
                encoding="utf-8")
        if proc.returncode != 0 and not proc.stdout.strip():
            raise ExecutorError(f"Claude Code завершился с кодом {proc.returncode}: {proc.stderr.strip()[:500]}")
        return parse_output(proc.stdout)
