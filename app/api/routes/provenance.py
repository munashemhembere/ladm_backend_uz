from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import get_db
from app.models.ladm import LadmEtlProvenanceLog
from app.schemas.ladm import ProvenanceOut
from app.core.security import require_auth

router = APIRouter(tags=["Provenance"])


@router.get("/provenance", response_model=List[ProvenanceOut],
            summary="ETL provenance audit log (read-only)")
async def list_provenance(
    operation: Optional[str] = Query(None, description="EXTRACT|TRANSFORM|LOAD|VALIDATE"),
    status: Optional[str] = Query(None, description="SUCCESS|WARNING|FAILED"),
    target_table: Optional[str] = None,
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """
    Full ETL audit trail — supports governance transparency and
    reproducibility requirements (Lemmen et al., 2015).
    All 18 prototype operations were logged as SUCCESS.
    """
    q = select(LadmEtlProvenanceLog).order_by(LadmEtlProvenanceLog.executed_at.desc())
    if operation:     q = q.where(LadmEtlProvenanceLog.operation == operation)
    if status:        q = q.where(LadmEtlProvenanceLog.status == status)
    if target_table:  q = q.where(LadmEtlProvenanceLog.target_table == target_table)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()
