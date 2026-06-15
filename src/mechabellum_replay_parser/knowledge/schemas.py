from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class KnowledgeChunk(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    patch_version: str | None = None
    title: str
    content: str
    tags: list[str] = []
    unit_names: list[str] = []
    topic: str
    priority: int = 0
