from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_db
from app.models.extraction import ExtractionRecord, ExtractionTemplate
from app.models.project import Project
from app.models.user import User
from app.schemas.extraction import (
    ExtractionRecordCreate,
    ExtractionRecordPatch,
    ExtractionRecordResponse,
    ExtractionTemplateResponse,
)
from app.services.permissions import require_project_access
from app.services.extraction_service import create_extraction_record, ensure_builtin_template, export_records, list_records, patch_record

router = APIRouter(prefix="/extraction", tags=["extraction"])


async def _require_project(
    db: AsyncSession,
    project_id: UUID,
    user: User,
    *,
    required_role: str = "viewer",
) -> Project:
    project, _ = await require_project_access(db, project_id=project_id, user=user, required_role=required_role)
    return project


def _record_to_response(record: ExtractionRecord) -> ExtractionRecordResponse:
    return ExtractionRecordResponse(
        id=record.id,
        project_id=record.project_id,
        paper_id=record.paper_id,
        template_id=record.template_id,
        status=record.status,
        version=record.version,
        summary_json=record.summary_json,
        template_version=(record.summary_json or {}).get("template_version"),
        fields=[
            {
                "id": field.id,
                "field_name": field.field_name,
                "value_text": field.value_text,
                "auto_value_text": field.auto_value_text,
                "confidence": field.confidence,
                "source_page": field.source_page,
                "source_locator": field.source_locator,
                "manually_edited": field.manually_edited,
                "candidate_spans": (field.metadata_json or {}).get("candidate_spans", []),
                "validation_issues": (field.metadata_json or {}).get("validation_issues", []),
            }
            for field in record.field_values
        ],
    )


@router.get("/templates", response_model=list[ExtractionTemplateResponse])
async def get_templates(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    del user
    await ensure_builtin_template(db)
    result = await db.execute(select(ExtractionTemplate).order_by(ExtractionTemplate.is_builtin.desc(), ExtractionTemplate.name.asc()))
    templates = result.scalars().all()
    return [
        ExtractionTemplateResponse(
            id=item.id,
            name=item.name,
            slug=item.slug,
            description=item.description,
            discipline=item.discipline,
            is_builtin=item.is_builtin,
            schema_definition=item.schema_json,
        )
        for item in templates
    ]


@router.post("/records", response_model=ExtractionRecordResponse)
async def create_record(
    payload: ExtractionRecordCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project(db, payload.project_id, user, required_role="editor")
    record = await create_extraction_record(
        db,
        project_id=payload.project_id,
        paper_id=payload.paper_id,
        template_id=payload.template_id,
    )
    return _record_to_response(record)


@router.patch("/records/{record_id}", response_model=ExtractionRecordResponse)
async def update_record(
    record_id: UUID,
    payload: ExtractionRecordPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = (
        select(ExtractionRecord)
        .where(ExtractionRecord.id == record_id)
        .options(selectinload(ExtractionRecord.field_values))
    )
    result = await db.execute(stmt)
    record = result.scalars().first()
    if record is None:
        raise HTTPException(status_code=404, detail="Extraction record not found")
    await _require_project(db, record.project_id, user, required_role="editor")
    patched = await patch_record(db, record=record, status=payload.status, fields=payload.fields)
    await db.refresh(patched, attribute_names=["field_values"])
    return _record_to_response(patched)


@router.get("/records", response_model=list[ExtractionRecordResponse])
async def get_records(
    project_id: UUID = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project(db, project_id, user, required_role="viewer")
    return [_record_to_response(record) for record in await list_records(db, project_id=project_id)]


@router.get("/export")
async def export_extraction_records(
    project_id: UUID = Query(...),
    format: str = Query(..., pattern="^(csv|xlsx|json)$"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await _require_project(db, project_id, user, required_role="viewer")
    records = await list_records(db, project_id=project_id)
    return export_records(records, format)
