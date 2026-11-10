"""✓ · Спецификация функциональных требований. Детерминированная сборка пакета."""

import json
from datetime import datetime, timezone

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.agreement.contracts import Baseline
from reqpipe.domains.formalization.contracts import SpecBundle
from reqpipe.domains.result.contracts import SRSPackage

KIND_TITLES = {"pain": "Боль", "obligation": "Обязательство", "story": "История",
               "differentiator": "Дифференциатор", "entity": "Сущность"}


def _md_table(header: list[str], rows: list[list[str]]) -> str:
    def cell(v: str) -> str:
        return str(v).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines += ["| " + " | ".join(cell(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def render_markdown(baseline: dict, spec: SpecBundle) -> str:
    refs = spec.references()
    scenarios_by_fr: dict[str, list] = {}
    for sc in spec.scenarios:
        scenarios_by_fr.setdefault(sc.requirement_id, []).append(sc)
    tests_by_fr: dict[str, list] = {}
    for t in spec.tests:
        tests_by_fr.setdefault(t.requirement_id, []).append(t)

    out = [f"# Спецификация функциональных требований {baseline.get('version', 'v1.0')}", ""]
    status = "утверждена" if baseline.get("approved") else "НЕ утверждена"
    by = {"human": "человеком", "arbiter": "агентом-арбитром"}.get(baseline.get("approved_by", ""), "")
    out += [f"**Статус:** {status} {by} {baseline.get('approved_at', '')}".rstrip(), "",
            baseline.get("executive_summary", ""), ""]
    if spec.flags:
        out += ["## Важные отметки", ""] + [f"- ⚠ {f}" for f in spec.flags] + [""]
    if baseline.get("low_confidence_decisions"):
        out += ["## Решения с низкой уверенностью (просмотреть людям)", ""]
        out += [f"- {d}" for d in baseline["low_confidence_decisions"]] + [""]

    out += ["## Функциональные требования", ""]
    out.append(_md_table(
        ["ID", "Требование", "Приоритет", "Релиз", "Размер", "Источники"],
        [[fr.id, fr.statement, fr.priority or "—", fr.release or "—", fr.size or "—", ", ".join(fr.source_ids)]
         for fr in spec.requirements],
    ))
    out.append("")
    for fr in spec.requirements:
        out += [f"### {fr.id} · {fr.title}", "", fr.statement, ""]
        if fr.rationale:
            out += [f"*Обоснование:* {fr.rationale}", ""]
        meta = [f"EARS: {fr.ears}", f"Kano: {fr.kano or '—'}", f"Статус: {fr.status}"]
        if fr.entity_ids:
            meta.append("Сущности: " + ", ".join(fr.entity_ids))
        out += [" · ".join(meta), ""]
        for sc in scenarios_by_fr.get(fr.id, []):
            out += [f"**{sc.id}** ({sc.kind})", "", "```gherkin", sc.gherkin, "```", ""]
        if tests_by_fr.get(fr.id):
            out += ["Автотесты: " + ", ".join(f"{t.id} (`{t.file}`)" for t in tests_by_fr[fr.id]), ""]

    out += ["## Матрица трассируемости", ""]
    rows = [[KIND_TITLES[k], item.id, item.title, ", ".join(sorted(refs.get(item.id, set()))) or "НЕ ПОКРЫТО"]
            for k in KIND_TITLES for item in spec.catalog.get(k)]
    out += [_md_table(["Вид", "ID", "Название", "Требования"], rows), ""]

    if spec.benchmark:
        b = spec.benchmark
        out += ["## Карта превосходства", "",
                f"Взвешенная оценка: **{b.get('weighted_ours')}** против **{b.get('weighted_best_competitor')}** "
                f"у лучшего конкурента.", "", f"Почему перейдут к нам: {b.get('why_switch', '')}", ""]
    if spec.gate_log:
        out += ["## Журнал проверок", ""]
        out += [_md_table(["Фильтр", "Этап", "Вердикт", "Итог"],
                          [[g.gate or "—", g.element, g.verdict, g.summary] for g in spec.gate_log]), ""]
    if spec.risks:
        out += ["## Риски", ""]
        out += [_md_table(["ID", "Риск", "Влияние", "Мера"],
                          [[r.id, r.description, r.impact, r.mitigation] for r in spec.risks]), ""]
    if spec.decisions:
        out += ["## Журнал решений", ""]
        out += [f"- **{d.id}** {d.decision} — {d.rationale}" for d in spec.decisions] + [""]
    if spec.architecture:
        out += ["## Архитектурный эскиз", "", "```json", json.dumps(spec.architecture, ensure_ascii=False, indent=2),
                "```", ""]
    conds = baseline.get("conditions", {})
    if conds:
        out += ["## Условия выпуска baseline", ""] + [f"- {'✅' if ok else '❌'} {name}" for name, ok in conds.items()]
    return "\n".join(out) + "\n"


def run(ctx: Context) -> dict:
    baseline = ctx.input("signoff")
    spec = SpecBundle.model_validate(baseline.get("spec", {}))
    files = {
        "spec_markdown": ctx.write_output("SRS.md", render_markdown(baseline, spec)),
        "requirements_json": ctx.write_output("requirements.json", json.dumps(
            [fr.model_dump() for fr in spec.requirements], ensure_ascii=False, indent=2)),
        "spec_json": ctx.write_output("spec.json", json.dumps(spec.model_dump(), ensure_ascii=False, indent=2)),
    }
    return {
        "title": "Спецификация функциональных требований",
        "version": baseline.get("version", "v1.0"),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": files,
        "counts": {"requirements": len(spec.requirements), "scenarios": len(spec.scenarios),
                   "tests": len(spec.tests), "risks": len(spec.risks), "decisions": len(spec.decisions)},
        "flags": spec.flags,
    }


ELEMENT = Element(
    id="srs", num="✓", title="Спецификация функциональных требований", actor="Итоговый артефакт", kind="output",
    mode="deterministic",
    instructions=Instructions(
        purpose=(
            "Готовая основа для проектирования, оценки, разработки и тестирования системы. Каждое требование можно "
            "проследить до реальной потребности пользователя или обязательства, а каждое заявленное преимущество — "
            "до конкретных требований."
        ),
        methods=(
            "Функциональные требования с ID, приоритетами и источниками",
            "Критерии приёмки Given / When / Then",
            "Набор автотестов, привязанных к FR-ID",
            "Глоссарий, модель данных и бизнес-правила",
            "Матрица трассируемости от болей до тестов",
            "Карта превосходства над конкурентами",
            "Журнал решений с обоснованиями",
        ),
        done="Все quality gates (G0–G6) пройдены, baseline утверждён людьми.",
    ),
    consumes=(Consumes("signoff", Baseline),),
    output=SRSPackage,
    run=run,
)
