"""
Pydantic v2 schemas for request/response validation.
Each table has a Create, Out (and Update where needed) schema.
"""
from __future__ import annotations
from datetime import datetime, date
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr, ConfigDict


class OrmBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ── Auth ─────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: str = "user"

class UserOut(OrmBase):
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime


# ── Party ────────────────────────────────────────────────────

class PartyCreate(BaseModel):
    party_id: str
    name: str
    party_type: Optional[str] = None  # naturalPerson | nonNaturalPerson
    uz_role: Optional[str] = None
    ext_id: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    gender: Optional[str] = None
    party_ext_type: Optional[str] = None
    is_active: Optional[bool] = True

class PartyOut(OrmBase):
    party_id: str
    name: str
    party_type: Optional[str]
    uz_role: Optional[str]
    ext_id: Optional[str]
    email: Optional[str]
    department: Optional[str]
    gender: Optional[str]
    party_ext_type: Optional[str]
    is_active: Optional[bool]
    begin_lifespan_version: Optional[datetime]
    end_lifespan_version: Optional[datetime]

class PartyUpdate(BaseModel):
    name: Optional[str] = None
    uz_role: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    is_active: Optional[bool] = None


# ── Group Party ───────────────────────────────────────────────

class GroupPartyCreate(BaseModel):
    group_id: str
    name: str
    group_type: Optional[str] = None

class GroupPartyOut(OrmBase):
    group_id: str
    name: str
    group_type: Optional[str]
    begin_lifespan_version: Optional[datetime]
    end_lifespan_version: Optional[datetime]


# ── Party Member ──────────────────────────────────────────────

class PartyMemberCreate(BaseModel):
    group_id: str
    party_id: str
    role_in_group: Optional[str] = None

class PartyMemberOut(OrmBase):
    member_id: int
    group_id: str
    party_id: str
    role_in_group: Optional[str]
    begin_lifespan_version: Optional[datetime]
    end_lifespan_version: Optional[datetime]


# ── BAUnit ────────────────────────────────────────────────────

class BaunitCreate(BaseModel):
    baunit_id: str
    name: str
    type: Optional[str] = "basicUnit"
    unit_type: Optional[str] = None
    building_code: Optional[str] = None
    description: Optional[str] = None

class BaunitOut(OrmBase):
    baunit_id: str
    name: str
    type: Optional[str]
    unit_type: Optional[str]
    building_code: Optional[str]
    description: Optional[str]
    begin_lifespan_version: Optional[datetime]
    end_lifespan_version: Optional[datetime]


# ── RRR ──────────────────────────────────────────────────────

class RRRCreate(BaseModel):
    rrr_id: str
    type: Optional[str] = None  # Ownership|Use|Occupancy|Maintenance|...
    party_id: Optional[str] = None
    baunit_id: Optional[str] = None
    status: Optional[str] = "Active"
    rrr_subclass: Optional[str] = None  # LA_Right|LA_Restriction|LA_Responsibility
    description: Optional[str] = None

class RRROut(OrmBase):
    rrr_id: str
    type: Optional[str]
    party_id: Optional[str]
    baunit_id: Optional[str]
    status: Optional[str]
    rrr_subclass: Optional[str]
    description: Optional[str]
    begin_lifespan_version: Optional[datetime]
    end_lifespan_version: Optional[datetime]


# ── Sources ───────────────────────────────────────────────────

class SourceCreate(BaseModel):
    source_id: str
    type: Optional[str] = None
    description: Optional[str] = None

class SourceOut(OrmBase):
    source_id: str
    type: Optional[str]
    description: Optional[str]
    begin_lifespan_version: Optional[datetime]

class AdminSourceCreate(BaseModel):
    source_id: str
    type: str
    official_identifier: Optional[str] = None
    acceptance_date: Optional[date] = None
    ext_archive_id: Optional[str] = None
    description: Optional[str] = None

class AdminSourceOut(OrmBase):
    source_id: str
    type: str
    official_identifier: Optional[str]
    acceptance_date: Optional[date]
    ext_archive_id: Optional[str]
    description: Optional[str]
    begin_lifespan_version: datetime
    end_lifespan_version: Optional[datetime]

class SpatialSourceCreate(BaseModel):
    source_id: str
    type: str
    official_identifier: Optional[str] = None
    acceptance_date: Optional[date] = None
    ext_archive_id: Optional[str] = None
    description: Optional[str] = None

class SpatialSourceOut(OrmBase):
    source_id: str
    type: str
    official_identifier: Optional[str]
    acceptance_date: Optional[date]
    ext_archive_id: Optional[str]
    description: Optional[str]
    begin_lifespan_version: datetime
    end_lifespan_version: Optional[datetime]


# ── Spatial Unit ──────────────────────────────────────────────

class SpatialUnitCreate(BaseModel):
    su_id: str
    baunit_id: Optional[str] = None
    global_id_ifc: Optional[str] = None
    label: Optional[str] = None
    su_type: Optional[str] = None   # parcel | building | room
    area_m2: Optional[float] = None
    capacity: Optional[int] = None
    surface_relation: Optional[str] = None
    dimension: Optional[str] = None  # <-- ADDED: Dynamic tracking for 2D vs 3D boundaries

class SpatialUnitOut(OrmBase):
    su_id: str
    baunit_id: Optional[str]
    global_id_ifc: Optional[str]
    label: Optional[str]
    su_type: Optional[str]
    area_m2: Optional[float]
    capacity: Optional[int]
    surface_relation: Optional[str]
    dimension: Optional[str]         # <-- ADDED: Ensures data grid passes dimension details

class SpatialUnitGeoOut(BaseModel):
    """GeoJSON Feature response — geometry in WGS84 (EPSG:4326)"""
    type: str = "Feature"
    properties: Dict[str, Any]
    geometry: Optional[Dict[str, Any]]  # null if no geom stored


# ── IFC Mapping ───────────────────────────────────────────────

class IFCMappingCreate(BaseModel):
    spatial_unit_id: str
    ifc_global_id: Optional[str] = None  # <-- UPDATED: Allows creation tasks without immediate IDs
    ifc_entity_type: str
    ifc_name: Optional[str] = None
    ifc_source_file: Optional[str] = None
    mapped_by: Optional[str] = None

class IFCMappingOut(OrmBase):
    id: int
    spatial_unit_id: str
    ifc_global_id: Optional[str]         # <-- UPDATED: Prevents validation errors when processing NULL entries
    ifc_entity_type: str
    ifc_name: Optional[str]
    ifc_source_file: Optional[str]
    mapped_at: datetime
    mapped_by: Optional[str]


# ── Full spatial unit record (GeoBIM click-to-query) ──────────

class RRRSummary(BaseModel):
    rrr_id: str
    type: Optional[str]
    rrr_subclass: Optional[str]
    description: Optional[str]
    status: Optional[str]
    party_name: Optional[str]
    party_role: Optional[str]

class FullSpatialUnitRecord(BaseModel):
    """
    Complete LADM record for any spatial unit.
    Used by the GeoBIM frontend button-click workflow.
    """
    su_id: str
    label: Optional[str]
    su_type: Optional[str]
    area_m2: Optional[float]
    capacity: Optional[int]
    surface_relation: Optional[str]
    global_id_ifc: Optional[str]
    dimension: Optional[str]             # <-- ADDED: Passes boundary structural metadata to frontend clicks
    baunit_name: Optional[str]
    baunit_type: Optional[str]
    rrrs: List[RRRSummary]
    ifc_mappings: List[IFCMappingOut]
    geometry_wgs84: Optional[Dict[str, Any]]  # reprojected to EPSG:4326


# ── Provenance ────────────────────────────────────────────────

class ProvenanceOut(OrmBase):
    id: int
    operation: str
    status: str
    executed_at: datetime
    source_file: Optional[str]
    target_table: Optional[str]
    records_affected: int
    message: Optional[str]
    script_name: Optional[str]
    executed_by: Optional[str]