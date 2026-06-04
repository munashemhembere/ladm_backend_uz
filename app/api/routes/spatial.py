"""
Spatial Unit Package routes.

Key endpoints:
  GET /spatial-units              — all spatial units (no geometry)
  GET /spatial-units/{su_id}      — single unit (no geometry)
  GET /spatial-units/{su_id}/full-record  — full LADM record + RRRs + IFC + geom (WGS84)
  GET /spatial-units/parcels/geojson  — ALL parcels (su_type='parcel') as GeoJSON FeatureCollection,
                                        geometry transformed EPSG:20936 → EPSG:4326 for GeoBIM frontend
  GET /spatial-units/{su_id}/geojson  — single spatial unit as GeoJSON Feature (WGS84)
  POST /bim-mappings              — create IFC mapping
  GET  /bim-mappings/resolve      — resolve IFC GlobalId to LADM record
"""
import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload
from geoalchemy2.functions import ST_AsGeoJSON, ST_Transform

from app.db.base import get_db
from app.models.ladm import (
    LaSpatialUnit, LaSpatialUnitBaunit, LaSpatialUnitIFCMapping,
    LaSpatialUnitSpatialSource, LaRRR, LaRRRBaunit, LaParty
)
from app.schemas.ladm import (
    SpatialUnitCreate, SpatialUnitOut, SpatialUnitGeoOut,
    IFCMappingCreate, IFCMappingOut,
    FullSpatialUnitRecord, RRRSummary,
)
from app.core.security import require_auth, require_admin

router = APIRouter(tags=["Spatial Unit Package"])

TARGET_SRID = 4326   # WGS84 for GeoBIM frontend (CesiumJS / Leaflet)


# ── Helper: geometry → GeoJSON dict reprojected to WGS84 ─────

async def _geom_to_wgs84(db: AsyncSession, su_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch the geometry for a spatial unit, transform from EPSG:20936
    to EPSG:4326 (WGS84), and return as a GeoJSON geometry dict.
    Returns None if the spatial unit has no geometry stored.
    """
    result = await db.execute(
        select(ST_AsGeoJSON(ST_Transform(LaSpatialUnit.geom, TARGET_SRID)))
        .where(LaSpatialUnit.su_id == su_id)
    )
    raw = result.scalar_one_or_none()
    if raw:
        return json.loads(raw)
    return None


# ── Spatial Units (no geometry) ───────────────────────────────

@router.get("/spatial-units", response_model=List[SpatialUnitOut],
            summary="List all spatial units (attributes only, no geometry)")
async def list_spatial_units(
    su_type: Optional[str] = Query(None, description="parcel | building | room"),
    baunit_id: Optional[str] = None,
    surface_relation: Optional[str] = None,
    search: Optional[str] = Query(None, description="Search by label"),
    skip: int = 0, limit: int = 200,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaSpatialUnit)
    if su_type:          q = q.where(LaSpatialUnit.su_type == su_type)
    if baunit_id:        q = q.where(LaSpatialUnit.baunit_id == baunit_id)
    if surface_relation: q = q.where(LaSpatialUnit.surface_relation == surface_relation)
    if search:           q = q.where(LaSpatialUnit.label.ilike(f"%{search}%"))
    result = await db.execute(q.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("/spatial-units", response_model=SpatialUnitOut, status_code=201)
async def create_spatial_unit(
    data: SpatialUnitCreate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    su = LaSpatialUnit(**data.model_dump())
    db.add(su)
    await db.flush()
    await db.refresh(su)
    return su


@router.get("/spatial-units/{su_id}", response_model=SpatialUnitOut)
async def get_spatial_unit(
    su_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    result = await db.execute(select(LaSpatialUnit).where(LaSpatialUnit.su_id == su_id))
    su = result.scalar_one_or_none()
    if not su: raise HTTPException(404, "Spatial unit not found")
    return su


# ── GeoJSON single unit (EPSG:20936 → EPSG:4326) ──────────────

@router.get("/spatial-units/{su_id}/geojson",
            response_model=SpatialUnitGeoOut,
            summary="Single spatial unit as GeoJSON Feature — geometry in WGS84 (EPSG:4326)")
async def spatial_unit_geojson(
    su_id: str, db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """
    Returns the spatial unit geometry reprojected from EPSG:20936
    (Arc 1960 / UTM Zone 36S — stored CRS) to EPSG:4326 (WGS84)
    for direct consumption by GeoBIM / CesiumJS / Leaflet frontends.
    """
    result = await db.execute(
        select(LaSpatialUnit).where(LaSpatialUnit.su_id == su_id)
    )
    su = result.scalar_one_or_none()
    if not su: raise HTTPException(404, "Spatial unit not found")

    geom_wgs84 = await _geom_to_wgs84(db, su_id)

    return SpatialUnitGeoOut(
        type="Feature",
        properties={
            "su_id":             su.su_id,
            "label":             su.label,
            "su_type":           su.su_type,
            "area_m2":           float(su.area_m2) if su.area_m2 else None,
            "capacity":          su.capacity,
            "surface_relation":  su.surface_relation,
            "global_id_ifc":     su.global_id_ifc,
            "baunit_id":         su.baunit_id,
            "crs":               "EPSG:4326",
        },
        geometry=geom_wgs84,
    )


# ── Parcels GeoJSON FeatureCollection ────────────────────────

@router.get("/spatial-units/parcels/geojson",
            summary="All parcel spatial units as GeoJSON FeatureCollection — geometry in WGS84",
            response_model=Dict[str, Any])
async def parcels_geojson(
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """
    Returns ALL spatial units of type 'parcel' as a GeoJSON FeatureCollection.

    Geometry is transformed from the stored CRS EPSG:20936
    (Arc 1960 / UTM Zone 36S) to EPSG:4326 (WGS84) using PostGIS
    ST_Transform — making it immediately consumable by CesiumJS,
    Leaflet, Mapbox, or any GeoBIM frontend without further conversion.

    For the UZ prototype this returns Stand 7777A (SU001) — the
    191.75-hectare campus parcel boundary.
    """
    result = await db.execute(
        select(
            LaSpatialUnit,
            ST_AsGeoJSON(ST_Transform(LaSpatialUnit.geom, TARGET_SRID)).label("geojson_str")
        ).where(LaSpatialUnit.su_type == "parcel")
    )
    rows = result.all()

    features = []
    for su, geojson_str in rows:
        features.append({
            "type": "Feature",
            "properties": {
                "su_id":            su.su_id,
                "label":            su.label,
                "su_type":          su.su_type,
                "area_m2":          float(su.area_m2) if su.area_m2 else None,
                "surface_relation": su.surface_relation,
                "global_id_ifc":    su.global_id_ifc,
                "baunit_id":        su.baunit_id,
                "crs":              "EPSG:4326",
            },
            "geometry": json.loads(geojson_str) if geojson_str else None,
        })

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
        "count": len(features),
    }


# ── All spatial units as GeoJSON FeatureCollection ────────────

@router.get("/spatial-units/all/geojson",
            summary="All spatial units with geometry as GeoJSON FeatureCollection (WGS84)",
            response_model=Dict[str, Any])
async def all_spatial_units_geojson(
    su_type: Optional[str] = Query(None, description="Filter by type: parcel|building|room"),
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """
    Returns all spatial units that have a stored geometry as a
    GeoJSON FeatureCollection, geometries transformed to EPSG:4326.
    Useful for rendering the full campus map overlay in the frontend.
    """
    q = select(
        LaSpatialUnit,
        ST_AsGeoJSON(ST_Transform(LaSpatialUnit.geom, TARGET_SRID)).label("geojson_str")
    ).where(LaSpatialUnit.geom.isnot(None))

    if su_type:
        q = q.where(LaSpatialUnit.su_type == su_type)

    result = await db.execute(q)
    rows = result.all()

    features = []
    for su, geojson_str in rows:
        if geojson_str:
            features.append({
                "type": "Feature",
                "properties": {
                    "su_id":   su.su_id, "label": su.label,
                    "su_type": su.su_type,
                    "area_m2": float(su.area_m2) if su.area_m2 else None,
                    "crs":     "EPSG:4326",
                },
                "geometry": json.loads(geojson_str),
            })

    return {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": features,
        "count": len(features),
    }


# ── Full LADM Record (button-click GeoBIM workflow) ───────────

@router.get("/spatial-units/{su_id}/full-record",
            response_model=FullSpatialUnitRecord,
            summary="Full LADM record — geometry + RRRs + parties + IFC (GeoBIM button endpoint)")
async def spatial_unit_full_record(
    su_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_auth)
):
    """
    Full LADM record for any spatial unit — used by GeoBIM frontend button click.

    Returns the complete governance record:
    - Attributes (label, su_type, area_m2, capacity, surface_relation, dimension)
    - BAUnit name and type
    - All associated RRRs with party name and role
    - All IFC GlobalId mappings
    - Geometry reprojected to EPSG:4326 (WGS84) as GeoJSON

    Integration pattern:
      frontend button (room/building/parcel)
      → sends su_id to this endpoint
      → receives full LADM governance record
      → displays in info panel
    """
    # Load spatial unit with baunit and ifc mappings
    result = await db.execute(
        select(LaSpatialUnit)
        .options(
            selectinload(LaSpatialUnit.baunit),
            selectinload(LaSpatialUnit.ifc_mappings),
        )
        .where(LaSpatialUnit.su_id == su_id)
    )
    su = result.scalar_one_or_none()
    if not su:
        raise HTTPException(404, f"Spatial unit '{su_id}' not found")

    # Get RRRs — direct baunit_id link
    rrr_summaries = []
    if su.baunit_id:
        rrr_result = await db.execute(
            select(LaRRR, LaParty)
            .outerjoin(LaParty, LaRRR.party_id == LaParty.party_id)
            .where(LaRRR.baunit_id == su.baunit_id)
        )
        for rrr, party in rrr_result.all():
            rrr_summaries.append(RRRSummary(
                rrr_id=rrr.rrr_id,
                type=rrr.type,
                rrr_subclass=rrr.rrr_subclass,
                description=rrr.description,
                status=rrr.status,
                party_name=party.name if party else None,
                party_role=party.uz_role if party else None,
            ))

        # Also get RRRs via la_rrr_baunit junction table
        rrr_join_result = await db.execute(
            select(LaRRR, LaParty)
            .outerjoin(LaParty, LaRRR.party_id == LaParty.party_id)
            .join(LaRRRBaunit, LaRRR.rrr_id == LaRRRBaunit.rrr_id)
            .where(LaRRRBaunit.baunit_id == su.baunit_id)
        )
        existing_ids = {r.rrr_id for r in [x[0] for x in rrr_result.all()] if r} if False else \
                       {s.rrr_id for s in [summary for summary in rrr_summaries] if hasattr(s, 'rrr_id')}

        for rrr, party in rrr_join_result.all():
            if rrr.rrr_id not in {s.rrr_id for s in rrr_summaries}:
                rrr_summaries.append(RRRSummary(
                    rrr_id=rrr.rrr_id,
                    type=rrr.type,
                    rrr_subclass=rrr.rrr_subclass,
                    description=rrr.description,
                    status=rrr.status,
                    party_name=party.name if party else None,
                    party_role=party.uz_role if party else None,
                ))

    # IFC mappings
    ifc_maps = [IFCMappingOut.model_validate(m) for m in su.ifc_mappings]

    # Geometry → WGS84
    geom_wgs84 = await _geom_to_wgs84(db, su_id)

    return FullSpatialUnitRecord(
        su_id=su.su_id,
        label=su.label,
        su_type=su.su_type,
        area_m2=float(su.area_m2) if su.area_m2 else None,
        capacity=su.capacity,
        surface_relation=su.surface_relation,
        dimension=su.dimension,
        global_id_ifc=su.global_id_ifc,
        baunit_name=su.baunit.name if su.baunit else None,
        baunit_type=su.baunit.unit_type if su.baunit else None,
        rrrs=rrr_summaries,
        ifc_mappings=ifc_maps,
        geometry_wgs84=geom_wgs84,
    )

# ── IFC Mapping ───────────────────────────────────────────────

@router.get("/bim-mappings", response_model=List[IFCMappingOut],
            summary="List all LADM ↔ IFC GlobalId mappings")
async def list_ifc_mappings(
    su_id: Optional[str] = None,
    ifc_entity_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    q = select(LaSpatialUnitIFCMapping)
    if su_id:           q = q.where(LaSpatialUnitIFCMapping.spatial_unit_id == su_id)
    if ifc_entity_type: q = q.where(LaSpatialUnitIFCMapping.ifc_entity_type == ifc_entity_type)
    result = await db.execute(q)
    return result.scalars().all()


@router.post("/bim-mappings", response_model=IFCMappingOut, status_code=201,
             summary="Create a new LADM ↔ IFC mapping")
async def create_ifc_mapping(
    data: IFCMappingCreate,
    db: AsyncSession = Depends(get_db), _=Depends(require_admin)
):
    mapping = LaSpatialUnitIFCMapping(**data.model_dump())
    db.add(mapping)
    await db.flush()
    await db.refresh(mapping)
    return mapping


@router.get("/bim-mappings/resolve",
            summary="Resolve an IFC GlobalId to its full LADM spatial unit record")
async def resolve_ifc_global_id(
    ifc_id: str = Query(..., description="22-char IFC GlobalId from the GeoBIM model"),
    db: AsyncSession = Depends(get_db), _=Depends(require_auth)
):
    """
    Given any IFC GlobalId from the GeoBIM model, returns the
    corresponding LADM spatial unit record.

    GeoBIM button integration alternative: if IFC GlobalIds are
    available, the frontend can call this endpoint instead of
    /spatial-units/{su_id}/full-record.
    """
    result = await db.execute(
        select(LaSpatialUnitIFCMapping)
        .options(selectinload(LaSpatialUnitIFCMapping.spatial_unit)
                 .selectinload(LaSpatialUnit.baunit))
        .where(LaSpatialUnitIFCMapping.ifc_global_id == ifc_id)
    )
    mapping = result.scalar_one_or_none()
    if not mapping:
        raise HTTPException(404, f"No LADM record found for IFC GlobalId: {ifc_id}")

    su = mapping.spatial_unit
    return {
        "ifc_global_id":   mapping.ifc_global_id,
        "ifc_entity_type": mapping.ifc_entity_type,
        "ifc_name":        mapping.ifc_name,
        "su_id":           su.su_id,
        "label":           su.label,
        "su_type":         su.su_type,
        "baunit_name":     su.baunit.name if su.baunit else None,
    }
