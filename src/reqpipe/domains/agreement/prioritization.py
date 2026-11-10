"""6.2 · Приоритизация: Kano + RICE + MoSCoW."""

from reqpipe.core import Consumes, Context, Element, Instructions
from reqpipe.domains.agreement.contracts import SIZE_EFFORT, BacklogDraft, FeasibilityReport, PrioritizedBacklog
from reqpipe.domains.formalization.contracts import SpecBundle


def rice(reach: float, impact: float, confidence: float, effort: float) -> float:
    return round(reach * impact * confidence / max(effort, 0.1), 2)


def finalize(ctx: Context, data: dict) -> dict:
    spec = SpecBundle.model_validate(ctx.input("feasibility").get("spec", {}))
    sizes = {fr.id: fr.size for fr in spec.requirements}
    items = []
    for item in data.get("items", []):
        effort = item.get("effort") or SIZE_EFFORT.get(sizes.get(item["requirement_id"], "M"), 3)
        items.append({**item, "effort": effort,
                      "rice": rice(item.get("reach", 100), item.get("impact", 1), item.get("confidence", 0.8), effort)})
    items.sort(key=lambda i: i["rice"], reverse=True)
    by_id = {i["requirement_id"]: i for i in items}
    for fr in spec.requirements:
        if fr.id in by_id:
            fr.kano, fr.priority, fr.release = by_id[fr.id]["kano"], by_id[fr.id]["moscow"], by_id[fr.id]["release"]
    return {**data, "items": items, "spec": spec.model_dump()}


def example(ctx: Context) -> dict:
    spec = SpecBundle.model_validate(ctx.input("feasibility").get("spec", {}))
    items = []
    for n, fr in enumerate(spec.requirements):
        must = n == 0 or any(s.startswith("OBL-") for s in fr.source_ids)
        items.append({"requirement_id": fr.id, "kano": "must" if must else "attractive", "reach": 1000 - n * 100,
                      "impact": 2 if must else 1, "confidence": 0.8, "moscow": "must" if must else "should",
                      "release": "MVP" if n < 3 else "R2"})
    return {"items": items, "mvp_rationale": "MVP закрывает обязательные функции и первый дифференциатор",
            "wont_have_rationale": ""}


ELEMENT = Element(
    id="prioritize", num="6.2", title="Приоритизация", actor="Скилл Kano + RICE", kind="skill",
    instructions=Instructions(
        purpose=(
            "Определить порядок реализации так, чтобы уже первый релиз давал паритет по базе и хотя бы один "
            "ощутимый дифференциатор."
        ),
        methods=(
            "Модель Кано: обязательные, одномерные и привлекательные функции",
            "RICE: охват × влияние × уверенность / трудозатраты (трудозатраты — из оценки реализуемости 6.1)",
            "MoSCoW для границ MVP",
            "Учёт зависимостей между требованиями",
        ),
        prompt=(
            "MVP должен закрывать все обязательные функции и хотя бы один дифференциатор. "
            "Обоснуй каждое решение «Won’t have»."
        ),
        done="Каждое требование имеет приоритет и целевой релиз; состав MVP обоснован.",
    ),
    consumes=(Consumes("feasibility", FeasibilityReport, ("spec",)),),
    output=PrioritizedBacklog,
    agent_output=BacklogDraft,
    finalize=finalize,
    example=example,
)
