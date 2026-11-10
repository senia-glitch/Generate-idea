"""4.5 · Генерация автотестов.

Код тестов записывается в ``output/tests``; дальше по цепочке идёт пакет
спецификации ``SpecBundle`` — требования, сценарии и ссылки на тесты.
"""

import re

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.formalization.contracts import AcceptanceSuite, AutoTestDraft, AutoTestSuite, SpecBundle


def safe_path(path: str) -> str:
    """Относительный путь внутри output/tests: без «..», дисков и абсолютных путей."""
    parts = [p for p in re.split(r"[\\/]+", path) if p and p not in (".", "..") and ":" not in p]
    return "/".join(parts) or "test.spec.ts"


def finalize(ctx: Context, data: dict) -> dict:
    suite = ctx.input("acceptance")
    contents: dict[str, list[str]] = {}   # несколько тестов в одном файле склеиваются, а не затирают друг друга
    for po in data.get("page_objects", []):
        contents.setdefault(safe_path(po["path"]), []).append(po["code"])
    refs = []
    for test in data.get("tests", []):
        rel = safe_path(test["file"])
        chunk = test["code"]
        if contents.get(rel) and chunk.startswith("import ") and chunk.split("\n", 1)[0] in contents[rel][0]:
            chunk = chunk.split("\n", 1)[1] if "\n" in chunk else ""   # не дублировать одинаковую строку import
        contents.setdefault(rel, []).append(chunk)
        refs.append({"id": test["id"], "scenario_id": test["scenario_id"],
                     "requirement_id": test["requirement_id"], "file": f"tests/{rel}"})
    files = [ctx.write_output(f"tests/{rel}", "\n".join(chunks)) for rel, chunks in contents.items()]
    spec = SpecBundle(
        requirements=suite.get("requirements", []),
        scenarios=suite.get("scenarios", []),
        tests=refs,
        catalog=suite.get("catalog", {}),
    )
    return {"framework": data.get("framework", "playwright"), "files": sorted(set(files)), "spec": spec.model_dump()}


def example(ctx: Context) -> dict:
    tests = []
    for n, sc in enumerate(ctx.input("acceptance").get("scenarios", []), 1):
        tests.append({
            "id": f"TC-{n:03d}", "scenario_id": sc["id"], "requirement_id": sc["requirement_id"], "title": sc["title"],
            "file": f"{sc['requirement_id'].lower()}.spec.ts",
            "code": (f"import {{ test, expect }} from '@playwright/test';\n"
                     f"// {sc['requirement_id']} · {sc['id']}\n"
                     f"test('{sc['id']} {sc['kind']}', async ({{ page }}) => {{\n"
                     f"  await page.goto('/');\n  await expect(page).toHaveTitle(/.+/);\n}});\n"),
        })
    return {"framework": "playwright", "page_objects": [{"path": "pages/app.page.ts",
                                                          "code": "export class AppPage {}\n"}], "tests": tests}


ELEMENT = Element(
    id="testgen", num="4.5", title="Генерация автотестов", actor="Агент — QA-инженер", kind="agent",
    capabilities=frozenset({"code"}),
    instructions=Instructions(
        purpose=(
            "Сделать спецификацию исполняемой: каждый критерий приёмки становится автотестом. Тесты прогоняются "
            "на прототипе этапа 5.5, а затем переходят в разработку как готовый регрессионный набор."
        ),
        methods=(
            "Генерация тестов Playwright / Cypress из Gherkin-сценариев (step definitions)",
            "Слой Page Object с абстрактными локаторами — тесты не привязаны к будущей вёрстке",
            "Тестовые данные из граничных значений бизнес-правил модели",
            "Каждый тест помечен FR-ID — для трассировки и анализа полноты (G3)",
        ),
        prompt=(
            "Один сценарий Gherkin — один тест. Не изобретай поведение: всё, чего нет в критериях приёмки, — "
            "повод вернуть требование на доработку, а не дописать тест."
        ),
        done="У каждого критерия приёмки есть исполняемый тест; тесты проходят на прототипе этапа 5.5.",
    ),
    consumes=(Consumes("acceptance", AcceptanceSuite),),
    output=AutoTestSuite,
    agent_output=AutoTestDraft,
    finalize=finalize,
    example=example,
)
