"""5.4 · G4 Симуляция пользователей."""

from reqpipe.core import Consumes, Context, Element, FeedbackItem, Instructions, Loop
from reqpipe.core.gates import evaluate_verdict
from reqpipe.domains.quality.common import pass_spec, spec_of
from reqpipe.domains.quality.contracts import CoverageReport, SimulationDraft, SimulationReport


def finalize(ctx: Context, data: dict) -> dict:
    return pass_spec(ctx, "coverage", data)


def evaluate(ctx: Context, artifact: dict):
    extra = [FeedbackItem(severity="major", target="reqwriter", refs=[r["stuck_at"]] if r.get("stuck_at") else [],
                          problem=f"Персона {r['persona_id']} застряла в сценарии {r['scenario_id']}: {r.get('notes', '')}")
             for r in artifact.get("runs", []) if r.get("outcome") == "stuck"]
    return evaluate_verdict(ctx, artifact, extra=extra)


def example(ctx: Context) -> dict:
    spec = spec_of(ctx, "coverage")
    personas = spec.catalog.ids("persona") or ["PER-001"]
    scenarios = spec.catalog.ids("scenario") or ["SCN-001"]
    runs = [{"persona_id": p, "scenario_id": s, "outcome": "passed", "notes": "Сценарий пройден без тупиков"}
            for p in personas for s in scenarios]
    return {"verdict": "pass", "summary": "Все персоны проходят ключевые сценарии", "findings": [], "runs": runs}


ELEMENT = Element(
    id="simulation", num="5.4", gate="G4", title="Симуляция пользователей", actor="Агенты-персоны", kind="multi",
    instructions=Instructions(
        purpose="Проверить спецификацию глазами пользователей до того, как написана хотя бы одна строка кода.",
        methods=(
            "Отдельный агент на каждую персону — с её целями, навыками и болями",
            "Прогон сценариев CJM только по тексту требований",
            "Фиксация тупиков, лишних шагов и неочевидных мест",
            "Сравнение с опытом в продуктах конкурентов",
        ),
        prompt=(
            "Ты — <персона>. Пройди сценарий, опираясь только на требования. "
            "Если система не говорит, что произойдёт дальше, — это дефект."
        ),
        done="Каждая персона проходит все ключевые сценарии без тупиков.",
    ),
    consumes=(Consumes("coverage", CoverageReport, ("spec",)),),
    loops=(Loop("reqwriter", "Тупики в сценариях", in_reference=False),),
    output=SimulationReport,
    agent_output=SimulationDraft,
    finalize=finalize,
    evaluate=evaluate,
    example=example,
)
