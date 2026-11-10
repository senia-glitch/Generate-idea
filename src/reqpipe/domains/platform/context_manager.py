"""Менеджер контекста: на каждом переходе собирает компактный пакет для агента.

Агент получает только данные по своим контрактам. Если пакет больше бюджета,
длинные тексты и списки сокращаются, а вместо них остаётся ссылка на полный
артефакт в базе знаний — агент может прочитать его сам.
"""

from __future__ import annotations

import json
from typing import Any

from reqpipe.core import Element, Instructions
from reqpipe.domains.platform.contracts import ContextPack

MAX_STR = 1500
MAX_LIST = 120


def _compress(value: Any, path: str, notes: list[str], max_str: int, max_list: int) -> Any:
    if isinstance(value, str) and len(value) > max_str:
        notes.append(f"{path}: текст сокращён с {len(value)} до {max_str} символов")
        return value[:max_str] + " …[сокращено]"
    if isinstance(value, list):
        items = value[:max_list]
        if len(value) > max_list:
            notes.append(f"{path}: показано {max_list} из {len(value)} элементов")
        return [_compress(v, f"{path}[{i}]", notes, max_str, max_list) for i, v in enumerate(items)]
    if isinstance(value, dict):
        return {k: _compress(v, f"{path}.{k}", notes, max_str, max_list) for k, v in value.items()}
    return value


def build_pack(element_id: str, inputs: dict[str, dict], budget_chars: int) -> ContextPack:
    """Пакет контекста: данные по контрактам, сжатые до бюджета."""
    size = len(json.dumps(inputs, ensure_ascii=False))
    if size <= budget_chars:
        return ContextPack(element_id=element_id, inputs=inputs, size_chars=size, budget_chars=budget_chars)
    notes: list[str] = []
    max_str, max_list = MAX_STR, MAX_LIST
    packed: dict[str, Any] = inputs
    for _ in range(6):   # постепенно ужимаем, пока не влезем в бюджет
        notes = []
        packed = {src: _compress(data, src, notes, max_str, max_list) for src, data in inputs.items()}
        size = len(json.dumps(packed, ensure_ascii=False))
        if size <= budget_chars:
            break
        max_str, max_list = max(200, max_str // 2), max(10, max_list // 2)
    refs = [f"полный артефакт {src}: artifacts/{src}.json" for src in inputs]
    return ContextPack(element_id=element_id, inputs=packed, truncated=notes + refs,
                       size_chars=size, budget_chars=budget_chars)


FORMAT_RULES = (
    "Язык — русский.",
    "ID — в указанных форматах (FR-001, PAIN-001 …) и стабильные между итерациями: исправляй, а не перенумеровывай.",
    "Ссылайся только на ID, которые есть во входных данных.",
    "Ничего не выдумывай: если данных нет, прямо напиши об этом в соответствующем поле.",
)


def render_task(element: Element, contracts: list, pack: ContextPack, *, schema: dict, result_file: str,
                domain_name: str = "",
                feedback: list, iteration: int, autonomous: bool, prepared: dict | None = None,
                repair_errors: list[str] | None = None) -> str:
    """Текст задачи для агента: карточка эталонной схемы + пакет контекста + формат ответа."""
    ins = element.instructions
    out = [f"# Задача этапа {element.num} «{element.title}»", "",
           f"**Роль:** {element.actor} · **Домен:** {domain_name or element.domain}" + (f" · **Фильтр:** {element.gate}" if element.gate else ""),
           ""]
    if autonomous and ins.auto_note:
        out += [f"> **Автономный режим.** {ins.auto_note}", ""]
    out += ["## Назначение", ins.purpose, "", "## Как работать"] + [f"- {m}" for m in ins.methods]
    prompt = ins.auto_prompt if autonomous and ins.auto_prompt else ins.prompt
    if prompt:
        out += ["", "## Ключевая инструкция", prompt]
    out += ["", "## Критерий готовности", ins.done]
    if "web" in element.capabilities:
        out += ["", "## Инструменты",
                "Используй веб-поиск и чтение страниц. Каждый факт подкрепляй источником: url, название, короткая "
                "цитата, дата обращения."]
    if element.mode == "external":
        out += ["", "## Что сдать на этом шаге",
                "Только прототип и план теста. Результаты сессий с людьми придут отдельно — их не придумывай."]

    out += ["", "## Входные данные (по контрактам)"]
    for c in contracts:
        note = f" — {c.note}" if c.note else ""
        fields = f" (поля: {', '.join(c.fields)})" if c.fields else ""
        out += [f"### От «{c.source}»{note}{fields}", "```json",
                json.dumps(pack.inputs.get(c.source, {}), ensure_ascii=False), "```"]
    if not contracts:
        out.append("Нет — это первый этап.")
    if pack.truncated:
        out += ["", "Менеджер контекста сократил пакет; полные версии можно прочитать из рабочей области:"]
        out += [f"- {t}" for t in pack.truncated]
    if prepared:
        out += ["", "## Результаты детерминированных проверок (учти их)", "```json",
                json.dumps(prepared, ensure_ascii=False), "```"]
    if feedback:
        out += ["", f"## Доработка — итерация {iteration + 1}", "Исправь замечания предыдущей версии:"]
        for f in feedback:
            refs = f" [{', '.join(f.refs)}]" if f.refs else ""
            hint = f" → {f.suggestion}" if f.suggestion else ""
            out.append(f"- ({f.severity}){refs} {f.problem}{hint}")
    if repair_errors:
        out += ["", "## Прошлый ответ не прошёл проверку контракта", "Исправь ошибки формата:"]
        out += [f"- {e}" for e in repair_errors[:40]]
    out += ["", "## Формат результата",
            "Верни **один JSON-объект** строго по схеме ниже — без пояснений вне JSON.",
            f"Если конвейер ведёшь ты сам (режим manual): запиши JSON в файл `{result_file}` и выполни "
            f"`reqpipe submit {element.id} \"{result_file}\"`.",
            "Правила:"] + [f"- {r}" for r in FORMAT_RULES]
    out += ["", "```json", json.dumps(schema, ensure_ascii=False), "```"]
    return "\n".join(out) + "\n"


ELEMENT = Element(
    id="ctx", num="", title="Менеджер контекста", actor="Агент-суммаризатор", kind="agent", mode="service",
    instructions=Instructions(
        purpose=(
            "Не даёт перегружать контекст следующих моделей: каждый агент получает сжатое и относящееся к его "
            "задаче, а не все артефакты целиком. Это дешевле, быстрее и снижает ошибки, когда важное «теряется» в "
            "середине длинного контекста."
        ),
        methods=(
            "Сводка фазы: факты, принятые решения, открытые вопросы, допущения",
            "Отдельный пакет под задачу каждого агента следующей фазы, а не одна общая сводка",
            "Детали не теряются: вместо них — ссылки на полные артефакты в базе знаний, агент подтягивает их по "
            "запросу (RAG)",
            "Контроль сжатия: ключевые ID требований, болей и решений не должны выпасть из пакета",
        ),
        prompt=(
            "Сжимай, но не обобщай: числа, ID, имена сущностей и формулировки решений сохраняй дословно. Всё, что "
            "опускаешь, заменяй ссылкой на артефакт."
        ),
        done="Каждый агент следующей фазы получил пакет в пределах своего бюджета токенов без потери ключевых ID и решений.",
    ),
)
