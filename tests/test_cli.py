"""Командная строка: init → run (mock) → status; сверка с эталоном; установка скиллов."""

import json
from pathlib import Path

from conftest import REFERENCE

from reqpipe.cli import main


def test_cli_end_to_end(tmp_path, capsys):
    ws = str(tmp_path / "ws")
    assert main(["init", "-w", ws, "--idea-text", "Сервис записи к врачу без звонков", "--executor", "mock",
                 "--autonomous"]) == 0
    assert main(["run", "-w", ws, "--no-input"]) == 0
    out = capsys.readouterr().out
    assert "Конвейер завершён" in out and "SRS.md" in out
    assert main(["status", "-w", ws, "--json"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert all(e["status"] == "done" for e in status["elements"].values())


def test_cli_manual_next_and_submit(tmp_path, capsys):
    ws = str(tmp_path / "ws")
    main(["init", "-w", ws, "--idea-text", "Идея"])
    capsys.readouterr()
    assert main(["next", "-w", ws, "--json"]) == 0
    action = json.loads(capsys.readouterr().out)
    assert action["action"] == "task" and action["element"] == "clarify"
    bad = tmp_path / "bad.json"
    bad.write_text('{"goal": "x"}', encoding="utf-8")
    assert main(["submit", "clarify", str(bad), "-w", ws]) == 2
    assert "problem" in capsys.readouterr().err


def test_cli_check_reference(capsys):
    assert main(["check-reference", "--html", str(REFERENCE)]) == 0
    assert "соответствует эталонной схеме" in capsys.readouterr().out


def test_cli_install_skills_into_project(tmp_path, capsys):
    assert main(["install-skills", "--dest", str(tmp_path)]) == 0
    for agent in (".claude", ".opencode"):
        for skill in ("reqpipe-pipeline", "reqpipe-stage"):
            text = (tmp_path / agent / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
            assert text.startswith("---\nname: " + skill)
            assert "{{REQPIPE}}" not in text and "-m reqpipe" in text   # вызов этой установки подставлен


def test_cli_install_skills_globally(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert main(["install-skills", "--global"]) == 0
    assert (tmp_path / ".claude" / "skills" / "reqpipe-pipeline" / "SKILL.md").exists()
    assert (tmp_path / ".config" / "opencode" / "skills" / "reqpipe-stage" / "SKILL.md").exists()


def test_skill_frontmatter_is_valid_yaml():
    """Значения без кавычек не должны содержать «: » — иначе агент не прочитает описание скилла."""
    root = Path(__file__).resolve().parents[1] / "src" / "reqpipe" / "skills"
    skills = list(root.rglob("SKILL.md"))
    assert len(skills) == 4
    for path in skills:
        text = path.read_text(encoding="utf-8")
        assert text.startswith("---\n")
        head = text.split("\n---\n", 1)[0].splitlines()[1:]
        fields = dict(line.split(": ", 1) for line in head)
        assert set(fields) == {"name", "description"}, path
        assert fields["name"] == path.parent.name
        for value in fields.values():
            if not value.startswith('"'):
                assert ": " not in value and not value.startswith(("'", "[", "{", "*", "&", "!", "|", ">")), path
            else:
                assert value.endswith('"') and '"' not in value[1:-1].replace('\\"', ""), path
