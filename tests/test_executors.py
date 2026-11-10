"""Разбор ответов Claude Code и OpenCode (форматы сняты с реальных вызовов)."""

import json
from pathlib import Path

from reqpipe.executors import claude_code, opencode
from reqpipe.executors.base import Task, extract_json, inline_refs

CLAUDE_ENVELOPE = json.dumps({
    "type": "result", "subtype": "success", "is_error": False, "total_cost_usd": 0.302112,
    "result": "{\"ok\":true,\"note\":\"тест\"}", "structured_output": {"ok": True, "note": "тест"},
}, ensure_ascii=False)

OPENCODE_EVENTS = "\n".join([
    '{"type":"step_start","part":{"type":"step-start"}}',
    '{"type":"text","part":{"type":"text","text":"{\\"ok\\": true, \\"note\\": \\"тест\\"}"}}',
    '{"type":"step_finish","part":{"type":"step-finish","reason":"stop","cost":0.0123}}',
])


def _task(tmp_path, **kw):
    return Task(element_id="voc", title="t", workspace=tmp_path, task_file=tmp_path / "t.md",
                schema={"type": "object", "properties": {"a": {"$ref": "#/$defs/X"}}, "$defs": {"X": {"type": "string"}}},
                schema_file=tmp_path / "s.json", result_file=tmp_path / "r.json", prompt="", **kw)


def test_claude_structured_output():
    result = claude_code.parse_output(CLAUDE_ENVELOPE)
    assert result.data == {"ok": True, "note": "тест"} and result.cost_usd == 0.302112


def test_claude_falls_back_to_result_text():
    env = json.loads(CLAUDE_ENVELOPE)
    env.pop("structured_output")
    env["result"] = "Готово:\n```json\n{\"ok\": true}\n```"
    assert claude_code.parse_output(json.dumps(env)).data == {"ok": True}


def test_claude_argv(tmp_path):
    argv = claude_code.build_argv("claude", _task(tmp_path, capabilities=frozenset({"web"}), model="opus"))
    assert argv[:2] == ["claude", "-p"] and "--json-schema" in argv
    assert "WebSearch" in argv[argv.index("--allowedTools") + 1]
    assert "$ref" not in argv[argv.index("--json-schema") + 1]
    assert argv[argv.index("--model") + 1] == "opus"


def test_claude_argv_without_model_uses_agent_default(tmp_path):
    assert "--model" not in claude_code.build_argv("claude", _task(tmp_path))


def test_opencode_events():
    result = opencode.parse_output(OPENCODE_EVENTS)
    assert result.data == {"ok": True, "note": "тест"} and result.cost_usd == 0.0123


def test_opencode_argv_attaches_task_last(tmp_path):
    argv = opencode.build_argv("opencode", _task(tmp_path, model="anthropic/x"), auto_approve=True)
    assert argv[1] == "run" and argv[-2] == "-f" and Path(argv[-1]).name == "t.md"
    assert "--auto" in argv and argv[argv.index("-m") + 1] == "anthropic/x"


def test_extract_json_variants():
    assert extract_json('{"a": 1}') == {"a": 1}
    assert extract_json('Вот ответ: {"a": {"b": "}"}} и всё') == {"a": {"b": "}"}}
    assert extract_json("нет json") is None


def test_inline_refs():
    flat = inline_refs({"properties": {"a": {"$ref": "#/$defs/X"}}, "$defs": {"X": {"type": "string"}}})
    assert flat == {"properties": {"a": {"type": "string"}}}
