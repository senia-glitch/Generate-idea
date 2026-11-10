"""Общие шаги фильтров домена: передача пакета спецификации дальше по цепочке."""

from reqpipe.core import Context
from reqpipe.domains.formalization.contracts import SpecBundle


def pass_spec(ctx: Context, source: str, data: dict, **extra) -> dict:
    """Взять ``spec`` у источника, отметить прохождение фильтра и вернуть артефакт.

    ``extra`` — поля пакета, которые фильтр обновляет (например, ``risks``).
    """
    spec = spec_of(ctx, source)
    spec.log_gate(ctx.element.gate or "", ctx.element.id, data.get("verdict", ""), data.get("summary", ""))
    merged = {**spec.model_dump(), **extra}
    return {**data, "spec": SpecBundle.model_validate(merged).model_dump()}


def spec_of(ctx: Context, source: str) -> SpecBundle:
    return SpecBundle.model_validate(ctx.input(source).get("spec", {}))
