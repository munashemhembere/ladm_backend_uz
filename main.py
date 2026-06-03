"""
LADM UZ Smart Campus Digital Twin — FastAPI Backend 
University of Zimbabwe | Geomatics Engineering Department

Built on your actual Supabase schema (ladm_uz_complete.sql).

Run locally:  uvicorn main:app --reload
Docs:         http://localhost:8000/docs
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.models import ladm  # noqa — import all models for SQLAlchemy to discover

from app.api.routes import auth, parties, admin, spatial, provenance


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are managed in Supabase — no create_all needed in production
    # For local dev without Supabase, uncomment the lines below:
    # from app.db.base import engine, Base
    # async with engine.begin() as conn:
    #     await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## LADM UZ Smart Campus Digital Twin API 

Backend for the governance-aware GeoBIM digital twin at the **University of Zimbabwe**.
Database: **Supabase (PostgreSQL 17 + PostGIS)**  |  Deploy: **Render**

### Key Architecture Points
- All geometry stored in **EPSG:20936** (Arc 1960 / UTM Zone 36S — UZ campus CRS)
- All GeoJSON responses transformed to **EPSG:4326 (WGS84)** for GeoBIM frontend
- JWT authentication with role-based access: `admin` | `planner` | `user`
- Parcel endpoint `/spatial-units/parcels/geojson` returns Stand 7777A campus boundary

### LADM Packages
| Package | Tables |
|---------|--------|
| Party | `la_party`, `la_groupparty`, `la_party_member` |
| Administrative | `la_baunit`, `la_rrr`, `la_rrr_baunit`, `la_rrr_admin_source` |
| Spatial Unit | `la_spatialunit`, `la_spatialunit_baunit`, `la_spatialunit_ifc_mapping` |
| Surveying | `la_source`, `la_AdministrativeSource`, `la_SpatialSource`, `la_spatialunit_spatial_source` |
| Provenance | `ladm_etl_provenance_log` |

### GeoBIM Button Integration
Complimentary study frontend assigns a `su_id` to each clickable button/panel:
```
GET /api/v1/spatial-units/{su_id}/full-record
```
Returns: geometry (WGS84) + BAUnit + all RRRs with party names + IFC mappings.

For the campus parcel boundary overlay:
```
GET /api/v1/spatial-units/parcels/geojson
```
Returns Stand 7777A as GeoJSON FeatureCollection in EPSG:4326.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────
V1 = "/api/v1"
app.include_router(auth.router,       prefix=V1)
app.include_router(parties.router,    prefix=V1)
app.include_router(admin.router,      prefix=V1)
app.include_router(spatial.router,    prefix=V1)
app.include_router(provenance.router, prefix=V1)


# ── Health / Root ─────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": settings.APP_VERSION, "app": settings.APP_NAME}

@app.get("/", tags=["System"])
async def root():
    return {
        "message": "LADM UZ Smart Campus Digital Twin API v2",
        "docs":    "/docs",
        "health":  "/health",
        "key_endpoints": {
            "parcel_geojson":     "/api/v1/spatial-units/parcels/geojson",
            "full_record":        "/api/v1/spatial-units/{su_id}/full-record",
            "resolve_ifc":        "/api/v1/bim-mappings/resolve?ifc_id=<GlobalId>",
            "all_rrrs":           "/api/v1/rrrs",
            "parties":            "/api/v1/parties",
        }
    }
