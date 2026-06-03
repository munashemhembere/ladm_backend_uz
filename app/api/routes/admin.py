from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.ladm import (
    LaBaunit, LaRRR, LaRRRBaunit, LaRRRAdminSource,
    LaSource, LaAdministrativeSource, LaSpatialSource
)
from app.schemas.ladm import (
    BaunitCreate, BaunitOut,
    RRRCreate, RRROut,
    SourceCreate, SourceOut,
    AdminSourceCreate, AdminSourceOut,
    SpatialSourceCreate, SpatialSourceOut,
)
from app.core.security import require_auth, require_admin

router = APIRouter(tags=["Administrative Package"])


# ── BAUnits ───────────────────────────────────────────────────

@router.get("/baunits", response_model=List[BaunitOut], summary="List all BAUnits")
async def list_baunits(
    unit_type: Optional[str] = None,
    building_code: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaBaunit)
    if unit_type:     q = q.where(LaBaunit.unit_type.ilike(f"%{unit_type}%"))
    if building_code: q = q.where(LaBaunit.building_code == building_code)
    if search:        q = q.where(LaBaunit.name.ilike(f"%{search}%"))
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/baunits", response_model=BaunitOut, status_code=201)
async def create_baunit(
    data: BaunitCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    ba = LaBaunit(**data.model_dump())
    db.add(ba)
    await db.flush()
    await db.refresh(ba)
    return ba


@router.get("/baunits/{baunit_id}", response_model=BaunitOut)
async def get_baunit(
    baunit_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(select(LaBaunit).where(LaBaunit.baunit_id == baunit_id))
    ba = result.scalar_one_or_none()
    if not ba: raise HTTPException(404, "BAUnit not found")
    return ba


@router.get("/baunits/{baunit_id}/rrrs", response_model=List[RRROut],
            summary="All RRRs for a BAUnit")
async def baunit_rrrs(
    baunit_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(
        select(LaRRR).where(
            (LaRRR.baunit_id == baunit_id) | LaRRR.rrr_id.in_(
                select(LaRRRBaunit.rrr_id).where(LaRRRBaunit.baunit_id == baunit_id)
            )
        )
    )
    return result.scalars().all()


# ── RRRs ──────────────────────────────────────────────────────

@router.get("/rrrs", response_model=List[RRROut], summary="List all RRRs")
async def list_rrrs(
    type: Optional[str] = Query(None, description="Ownership|Use|Occupancy|Maintenance|Admin Support|Statutory Oversight|Institutional|Technical"),
    status: Optional[str] = Query(None, description="Active|Inactive|Pending|Historic"),
    rrr_subclass: Optional[str] = Query(None, description="LA_Right|LA_Restriction|LA_Responsibility"),
    party_id: Optional[str] = None,
    baunit_id: Optional[str] = None,
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaRRR)
    if type:         q = q.where(LaRRR.type == type)
    if status:       q = q.where(LaRRR.status == status)
    if rrr_subclass: q = q.where(LaRRR.rrr_subclass == rrr_subclass)
    if party_id:     q = q.where(LaRRR.party_id == party_id)
    if baunit_id:    q = q.where(LaRRR.baunit_id == baunit_id)
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/rrrs", response_model=RRROut, status_code=201)
async def create_rrr(
    data: RRRCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    rrr = LaRRR(**data.model_dump())
    db.add(rrr)
    await db.flush()
    await db.refresh(rrr)
    return rrr


@router.get("/rrrs/active", response_model=List[RRROut], summary="Active RRRs only")
async def active_rrrs(db: AsyncSession = Depends(get_db), _=Depends(require_auth)):
    result = await db.execute(select(LaRRR).where(LaRRR.status == "Active"))
    return result.scalars().all()


@router.get("/rrrs/{rrr_id}", response_model=RRROut)
async def get_rrr(
    rrr_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(select(LaRRR).where(LaRRR.rrr_id == rrr_id))
    rrr = result.scalar_one_or_none()
    if not rrr: raise HTTPException(404, "RRR not found")
    return rrr


# ── Sources ───────────────────────────────────────────────────

@router.get("/sources", response_model=List[SourceOut])
async def list_sources(db: AsyncSession = Depends(get_db), _=Depends(require_auth)):
    result = await db.execute(select(LaSource))
    return result.scalars().all()


@router.get("/admin-sources", response_model=List[AdminSourceOut],
            summary="List administrative source documents")
async def list_admin_sources(
    source_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaAdministrativeSource)
    if source_type: q = q.where(LaAdministrativeSource.type == source_type)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/admin-sources", response_model=AdminSourceOut, status_code=201)
async def create_admin_source(
    data: AdminSourceCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    src = LaAdministrativeSource(**data.model_dump())
    db.add(src)
    await db.flush()
    await db.refresh(src)
    return src


@router.get("/spatial-sources", response_model=List[SpatialSourceOut],
            summary="List spatial source documents")
async def list_spatial_sources(db: AsyncSession = Depends(get_db), _=Depends(require_auth)):
    result = await db.execute(select(LaSpatialSource))
    return result.scalars().all()


@router.post("/spatial-sources", response_model=SpatialSourceOut, status_code=201)
async def create_spatial_source(
    data: SpatialSourceCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    src = LaSpatialSource(**data.model_dump())
    db.add(src)
    await db.flush()
    await db.refresh(src)
    return src
