from dataclasses import dataclass,field
from uuid import UUID

@dataclass(frozen=True)
class Evidence:
    page: int|None
    sheet: str|None
    cell: str|None
    text: str

@dataclass(frozen=True)
class ExtractedField:
    value: str|None
    evidence: tuple[Evidence,...]=()
    needs_review: bool=True

@dataclass(frozen=True)
class ExtractionResult:
    fields: dict[str,ExtractedField]
    lines: tuple[dict[str,ExtractedField],...]
    warnings: tuple[str,...]
    status: str='review'
    evidence: tuple[Evidence,...]=()

@dataclass(frozen=True)
class UploadResult:
    source_id: UUID
    job_id: UUID|None
    duplicate_order_ids: tuple[UUID,...]
