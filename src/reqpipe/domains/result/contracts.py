"""Публичные контракты домена «Результат»."""

from pydantic import Field

from reqpipe.core import Artifact


class SRSPackage(Artifact):
    title: str
    version: str
    generated_at: str
    files: dict[str, str] = Field(default_factory=dict, description="Назначение → путь в output/")
    counts: dict[str, int] = Field(default_factory=dict)
    flags: list[str] = Field(default_factory=list)
