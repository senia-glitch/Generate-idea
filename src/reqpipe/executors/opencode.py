"""Исполнитель OpenCode: ``opencode run --format json``.

Задача прикладывается файлом (``-f``), ответ собирается из JSON-событий
``text``, стоимость — из событий ``step_finish``.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime

from reqpipe.core.config import ExecutorConfig
from reqpipe.core.errors import ExecutorError
from reqpipe.executors.base import ExecutionResult, Task, extract_json

MESSAGE = ("Выполни задачу из приложенного файла полностью. "
           "Итоговый ответ - только JSON по схеме из задачи, без пояснений.")


def build_argv(command: str, task: Task, auto_approve: bool = False) -> list[str]:
    argv = [command, "run", MESSAGE, "--format", "json", "--dir", str(task.workspace)]
    if task.model:
        argv += ["-m", task.model]
    if auto_approve:
        argv.append("--auto")
    argv += list(task.extra_args)
    return argv + ["-f", str(task.task_file)]   # -f — массив, поэтому последним


def parse_output(stdout: str) -> ExecutionResult:
    texts: list[str] = []
    cost = 0.0
    errors: list[str] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        part = event.get("part") or {}
        if event.get("type") == "text" and part.get("text"):
            texts.append(part["text"])
        elif event.get("type") == "step_finish":
            cost += float(part.get("cost") or 0.0)
        elif event.get("type") == "error":
            errors.append(json.dumps(event.get("error") or event, ensure_ascii=False)[:500])
    data = None
    for text in reversed(texts):
        data = extract_json(text)
        if data is not None:
            break
    if data is None and texts:
        data = extract_json("\n".join(texts))
    if data is None and errors:
        raise ExecutorError("OpenCode сообщил об ошибке: " + "; ".join(errors))
    return ExecutionResult(data=data, raw=stdout, cost_usd=cost)


class OpenCodeExecutor:
    name = "opencode"

    def __init__(self, config: ExecutorConfig | None):
        self.config = config or ExecutorConfig(command="opencode")

    def execute(self, task: Task) -> ExecutionResult:
        command = shutil.which(self.config.command or "opencode")
        if not command:
            raise ExecutorError("Не найдена команда OpenCode (`opencode`). Установите OpenCode или укажите путь "
                                "в [executor.opencode] command.")
        argv = build_argv(command, task, self.config.auto_approve)
        try:
            proc = subprocess.run(argv, cwd=task.workspace, capture_output=True, text=True, encoding="utf-8",
                                  errors="replace", timeout=task.timeout_sec, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired as exc:
            raise ExecutorError(f"OpenCode не уложился в {task.timeout_sec} с") from exc
        if task.log_file:
            task.log_file.parent.mkdir(parents=True, exist_ok=True)
            task.log_file.write_text(
                f"# {datetime.now().isoformat()} exit={proc.returncode}\n{proc.stdout}\n--- stderr ---\n{proc.stderr}",
                encoding="utf-8")
        if proc.returncode != 0 and not proc.stdout.strip():
            raise ExecutorError(f"OpenCode завершился с кодом {proc.returncode}: {proc.stderr.strip()[:500]}")
        return parse_output(proc.stdout)
