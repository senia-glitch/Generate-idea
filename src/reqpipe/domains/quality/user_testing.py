"""5.5 · G5 Проверка на реальных пользователях.

Внешний этап в два шага:
1. агент собирает кликабельный прототип строго по требованиям и план теста;
2. результаты сессий приходят извне — от модератора, сервиса немодерируемого
   тестирования (``user_test_command``) или вручную через ``reqpipe submit-external``.
Пропуск этапа возможен только явным решением и помечается в спецификации.
"""

from html import escape

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import SimulationReport, UserTestPlan, UserTestReport, UserTestResults


def on_plan(ctx: Context, plan: dict) -> dict:
    path = ctx.write_output("prototype/index.html", plan.get("prototype_html", ""))
    return {**plan, "_prototype_path": path}


def finalize(ctx: Context, data: dict) -> dict:
    plan = {k: v for k, v in data["plan"].items() if not k.startswith("_")}
    results = data.get("results")
    flags: list[str] = []
    findings: list[dict] = []
    if data.get("waived"):
        verdict, summary = "pass", "Тест с пользователями пропущен по явному решению"
        flags.append(f"Проверка на реальных пользователях не проведена: {data.get('waiver_reason') or 'без причины'}")
    else:
        sessions = (results or {}).get("sessions", [])
        for s in sessions:
            for p in s.get("problems", []):
                if p.get("severity", "major") != "minor":
                    findings.append({"severity": p.get("severity", "major"), "target": "reqwriter",
                                     "refs": [p["requirement_id"]] if p.get("requirement_id") else [],
                                     "problem": f"{s['participant']}, задача {s['task_id']}: {p['description']}"})
        success = sum(1 for s in sessions if s.get("success"))
        verdict = "fail" if findings else "pass"
        summary = f"Успешных сессий: {success} из {len(sessions)}"
        if (results or {}).get("synthetic"):
            flags.append("Результаты теста с пользователями синтетические (mock) — нужна проверка на реальных людях")
    spec = spec_of(ctx, "simulation")
    report = {
        "verdict": verdict, "summary": summary, "findings": findings, "plan": plan, "results": results,
        "waived": bool(data.get("waived")), "waiver_reason": data.get("waiver_reason", ""),
        "prototype_path": data["plan"].get("_prototype_path", ""),
    }
    return pass_spec(ctx, "simulation", report, flags=spec.flags + flags)


def evaluate(ctx: Context, artifact: dict):
    return evaluate_verdict(ctx, artifact)


def example(ctx: Context) -> dict:
    spec = spec_of(ctx, "simulation")
    items = "".join(f"<li><button>{escape(r.id)}: {escape(r.title)}</button></li>" for r in spec.requirements)
    html = ("<!doctype html><html lang='ru'><meta charset='utf-8'><title>Прототип</title>"
            f"<body><h1>Прототип ключевых сценариев</h1><ul>{items}</ul></body></html>")
    scenarios = spec.catalog.ids("scenario") or ["SCN-001"]
    return {
        "prototype_html": html,
        "tasks": [{"id": f"UT-{n:03d}", "title": f"Пройти сценарий {s}", "scenario_id": s,
                   "requirement_ids": [r.id for r in spec.requirements[:2]]} for n, s in enumerate(scenarios, 1)],
        "participant_profile": "Представители персон PER-001 и PER-002",
        "participants": 6,
    }


def example_results(ctx: Context, plan: dict) -> dict:
    sessions = [{"participant": f"Участник {n}", "task_id": t["id"], "success": True, "time_sec": 240}
                for n in range(1, 4) for t in plan.get("tasks", [])]
    return {"sessions": sessions, "synthetic": True, "source": "mock"}


ELEMENT = Element(
    id="usertest", num="5.5", gate="G5", title="Проверка на реальных пользователях",
    actor="Пользователи ЦА + агент-прототипировщик", kind="human", mode="external",
    capabilities=frozenset({"code"}),
    instructions=Instructions(
        purpose=(
            "Все остальные проверки выполняет ИИ, а агенты-персоны склонны соглашаться и «усреднять» поведение. "
            "Подтвердить, что требования описывают продукт, который нужен людям и удобнее конкурентов, могут только "
            "реальные пользователи."
        ),
        methods=(
            "Генерация кликабельного прототипа ключевых сценариев прямо из требований и критериев приёмки",
            "Перед показом людям прототип проходит автотесты из 4.5 — значит, он действительно реализует требования",
            "Юзабилити-тест с 5–8 представителями целевых персон",
            "Те же задачи — в продукте основного конкурента, для прямого сравнения",
            "Каждая найденная проблема привязывается к конкретному требованию (FR-ID) и уходит на доработку",
        ),
        prompt=(
            "Собери прототип строго по требованиям: не добавляй поведения, которого нет в спецификации. "
            "Каждый экран помечай ID требований, которые он реализует."
        ),
        done=(
            "Реальные пользователи проходят ключевые сценарии без критичных проблем; найденные проблемы превращены "
            "в изменения требований."
        ),
        hitl="Решающее слово — за реальными пользователями: их замечания важнее выводов синтетических персон.",
        auto_note=(
            "Люди остаются только респондентами, но не принимают решений: агент сам набирает участников через "
            "сервис немодерируемого тестирования, запускает задания и разбирает записи."
        ),
    ),
    consumes=(Consumes("simulation", SimulationReport, ("spec",)),),
    loops=(Loop("reqwriter", "Проблемы пользователей", in_reference=False),),
    output=UserTestReport,
    agent_output=UserTestPlan,
    external_model=UserTestResults,
    on_plan=on_plan,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
    example_results=example_results,
)
