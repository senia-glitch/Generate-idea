"""0 · Сырая идея. Детерминированный элемент: регистрирует исходный текст."""

from datetime import datetime, timezone

from reqpipe.core import Context, Element, Instructions
from reqpipe.domains.intake.contracts import RawIdea


def run(ctx: Context) -> dict:
    text = ctx.idea_text.strip()
    if not text:
        raise ValueError("Идея пуста: передайте текст через `reqpipe init --idea` или файл idea.md")
    return RawIdea(
        text=text,
        received_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    ).model_dump()


ELEMENT = Element(
    id="idea", num="0", title="Сырая идея", actor="Автор идеи", kind="input",
    mode="deterministic",
    instructions=Instructions(
        purpose=(
            "Точка входа конвейера. Идея может быть сколь угодно сырой — неполной, противоречивой, "
            "с размытыми целями и скрытыми допущениями. От автора не требуется навыков бизнес-анализа: "
            "всю структуризацию берут на себя агенты."
        ),
        methods=(
            "Приём в любом формате: текст, аудио с транскрибацией, изображения, ссылки",
            "Сохранение исходной версии — с неё начинается цепочка трассировки «идея → требование»",
        ),
        done="Идея зарегистрирована в базе знаний и получила идентификатор.",
    ),
    output=RawIdea,
    run=run,
)
