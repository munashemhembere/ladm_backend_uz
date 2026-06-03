from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.base import get_db
from app.models.ladm import LaParty, LaGroupParty, LaPartyMember
from app.schemas.ladm import (
    PartyCreate, PartyOut, PartyUpdate,
    GroupPartyCreate, GroupPartyOut,
    PartyMemberCreate, PartyMemberOut,
)
from app.core.security import require_auth, require_admin

router = APIRouter(tags=["Party Package"])


# ── Parties ───────────────────────────────────────────────────

@router.get("/parties", response_model=List[PartyOut], summary="List all parties")
async def list_parties(
    uz_role: Optional[str] = None,
    party_type: Optional[str] = None,
    department: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = Query(None, description="Search by name or ext_id"),
    skip: int = 0, limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth),
):
    q = select(LaParty)
    if uz_role:      q = q.where(LaParty.uz_role == uz_role)
    if party_type:   q = q.where(LaParty.party_type == party_type)
    if department:   q = q.where(LaParty.department.ilike(f"%{department}%"))
    if is_active is not None: q = q.where(LaParty.is_active == is_active)
    if search:
        q = q.where(
            (LaParty.name.ilike(f"%{search}%")) | (LaParty.ext_id.ilike(f"%{search}%"))
        )
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/parties", response_model=PartyOut, status_code=201)
async def create_party(
    data: PartyCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    party = LaParty(**data.model_dump())
    db.add(party)
    await db.flush()
    await db.refresh(party)
    return party


@router.get("/parties/{party_id}", response_model=PartyOut)
async def get_party(
    party_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(select(LaParty).where(LaParty.party_id == party_id))
    party = result.scalar_one_or_none()
    if not party:
        raise HTTPException(404, "Party not found")
    return party


@router.patch("/parties/{party_id}", response_model=PartyOut)
async def update_party(
    party_id: str, data: PartyUpdate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    result = await db.execute(select(LaParty).where(LaParty.party_id == party_id))
    party = result.scalar_one_or_none()
    if not party: raise HTTPException(404, "Party not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(party, field, value)
    await db.flush()
    await db.refresh(party)
    return party


@router.get("/parties/by-role/{role}", response_model=List[PartyOut])
async def parties_by_role(
    role: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """Filter parties by UZ role: HOD | ACAD_STAFF | ADMIN_STAFF | STUDENT | TECH_STAFF | Institution | OWNER | EXT_AUTH"""
    result = await db.execute(
        select(LaParty).where(LaParty.uz_role == role, LaParty.is_active == True)
    )
    return result.scalars().all()


# ── Group Parties ──────────────────────────────────────────────

@router.get("/group-parties", response_model=List[GroupPartyOut])
async def list_group_parties(
    group_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaGroupParty)
    if group_type: q = q.where(LaGroupParty.group_type == group_type)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/group-parties", response_model=GroupPartyOut, status_code=201)
async def create_group_party(
    data: GroupPartyCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    gp = LaGroupParty(**data.model_dump())
    db.add(gp)
    await db.flush()
    await db.refresh(gp)
    return gp


@router.get("/group-parties/{group_id}", response_model=GroupPartyOut)
async def get_group_party(
    group_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(select(LaGroupParty).where(LaGroupParty.group_id == group_id))
    gp = result.scalar_one_or_none()
    if not gp: raise HTTPException(404, "Group party not found")
    return gp


# ── Party Members ─────────────────────────────────────────────

@router.get("/party-members", response_model=List[PartyMemberOut])
async def list_party_members(
    group_id: Optional[str] = None, party_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaPartyMember)
    if group_id: q = q.where(LaPartyMember.group_id == group_id)
    if party_id: q = q.where(LaPartyMember.party_id == party_id)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/party-members", response_model=PartyMemberOut, status_code=201)
async def add_party_member(
    data: PartyMemberCreate, db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    pm = LaPartyMember(**data.model_dump())
    db.add(pm)
    await db.flush()
    await db.refresh(pm)
    return pm
