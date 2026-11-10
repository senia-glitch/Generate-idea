"""Публичные контракты домена «Вход»."""

from pydantic import Field

from reqpipe.core import Artifact


class RawIdea(Artifact):
    idea_id: str = "IDEA-1"
    text: str = Field(description="Исходное описание замысла — как есть, без правок")
    attachments: list[str] = Field(default_factory=list, description="Пути или ссылки на приложенные материалы")
    received_at: str = ""
