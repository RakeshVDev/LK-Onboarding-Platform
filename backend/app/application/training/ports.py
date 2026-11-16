"""Application ports for Training, Question Ingestion, and Live Classes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from app.domain.training import (
    AssignableHostEntity,
    DepartmentEntity,
    LiveClassSessionEntity,
    ParsedQuestionCandidate,
)


@dataclass(slots=True)
class RawExtractedDocument:
    filename: str
    file_format: str
    table_rows: list[dict[str, str]] = field(default_factory=list)
    text_blocks: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class DocumentParserPort(Protocol):
    def parse(self, filename: str, content: bytes) -> RawExtractedDocument:
        ...


class QuestionBankRepository(Protocol):
    def template_exists(self, template_id: int) -> bool:
        ...

    def get_template_type(self, template_id: int) -> str | None:
        ...

    def bulk_insert(
        self,
        template_id: int,
        candidates: list[ParsedQuestionCandidate],
        created_by_user_id: int,
    ) -> list[int]:
        ...


class LiveClassRepository(Protocol):
    def get_department(self, department_id: int) -> DepartmentEntity | None:
        ...

    def list_departments_map(self) -> dict[int, str]:
        ...

    def create(self, session: LiveClassSessionEntity) -> LiveClassSessionEntity:
        ...

    def get_by_id(self, session_id: int) -> LiveClassSessionEntity | None:
        ...

    def list_sessions(self, department_id: int | None = None) -> list[LiveClassSessionEntity]:
        ...

    def update(self, session: LiveClassSessionEntity) -> LiveClassSessionEntity:
        ...

    def delete(self, session_id: int) -> bool:
        ...

    def get_host_user(self, user_id: int) -> AssignableHostEntity | None:
        ...

    def list_assignable_hosts(self, allowed_roles: tuple[str, ...]) -> list[AssignableHostEntity]:
        ...

