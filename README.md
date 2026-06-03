# LADM UZ Smart Campus Digital Twin — FastAPI Backend v2
**University of Zimbabwe | Geomatics Engineering Department**
Mhembere Munashe · R221660H · BSc Honours Land Administration and Management · 2025

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────────────┐
│  CLIENT LAYER                                                            │
│  GeoBIM Frontend (CesiumJS/Leaflet)  │  Swagger UI  │  REST Clients      │
└──────────────────────┬───────────────────────────────────────────────────┘
                       │  HTTPS  ·  JWT Bearer Token  ·  GeoJSON / JSON
┌──────────────────────▼───────────────────────────────────────────────────┐
│  FASTAPI BACKEND  (Render)                                               │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  main.py — FastAPI app · CORS · Router mounting                   │  │
│  └──────────────────────────┬─────────────────────────────────────────┘  │
│  ┌───────────────────────────▼─────────────────────────────────────────┐ │
│  │  ROUTES  (app/api/routes/)                                          │ │
│  │  auth.py · parties.py · admin.py · spatial.py · provenance.py      │ │
│  └───────────────────────────┬─────────────────────────────────────────┘ │
│  ┌───────────────────────────▼─────────────────────────────────────────┐ │
│  │  MODELS  (app/models/ladm.py) — 15 SQLAlchemy ORM tables           │ │
│  └───────────────────────────┬─────────────────────────────────────────┘ │
└──────────────────────────────┼───────────────────────────────────────────┘
                               │  asyncpg  ·  ST_Transform (EPSG:20936→4326)
┌──────────────────────────────▼───────────────────────────────────────────┐
│  DATA LAYER  (Supabase — PostgreSQL 17 + PostGIS)                        │
│  Database: ladm_uz  ·  Geometry stored: EPSG:20936                       │
│  GeoJSON served: EPSG:4326 (WGS84) — transformed by PostGIS             │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Structure

Built exactly from `ladm_uz_complete.sql`. All 15 tables:

```
PARTY PACKAGE
├── la_party          — natural/non-natural persons (16 prototype records)
├── la_groupparty     — groups: studentGroup, staffGroup, adminGroup, etc. (7 records)
└── la_party_member   — party ↔ group membership with roles (16 records)

ADMINISTRATIVE PACKAGE
├── la_baunit             — basic admin units: Campus, Building, GF, FF (4 records)
├── la_rrr                — rights, restrictions, responsibilities (16 records)
├── la_rrr_baunit         — many-to-many: RRR ↔ BAUnit
└── la_rrr_admin_source   — many-to-many: RRR ↔ AdminSource

SPATIAL UNIT PACKAGE
├── la_spatialunit           — spatial units (parcel/building/room) + PostGIS geom EPSG:20936
├── la_spatialunit_baunit    — many-to-many: SU ↔ BAUnit (with lifespan)
├── la_spatialunit_ifc_mapping   — LADM ↔ IFC GlobalId bridge (empty until IFC matures)
└── la_spatialunit_spatial_source — SU ↔ SpatialSource

SURVEYING PACKAGE
├── la_source                — generic source records
├── la_AdministrativeSource  — 10 admin sources (Title Deed, Acts, Contracts, etc.)
├── la_SpatialSource         — 4 spatial sources (Survey Diagram, RTK, Arch Plan, Drone)
└── la_source_spatialunit    — la_source ↔ la_spatialunit

PROVENANCE
└── ladm_etl_provenance_log  — ETL audit trail (all operations logged)

AUTH
└── app_user  — application users with roles: admin | planner | user
```

---

## Project File Structure

```
ladm_uz_v2/
├── main.py                      ← FastAPI app entry point
├── requirements.txt             ← Python dependencies
├── .env.example                 ← Environment variables template
├── Procfile                     ← Render deployment command
│
├── app/
│   ├── core/
│   │   ├── config.py            ← Settings (pydantic-settings + .env)
│   │   └── security.py          ← JWT tokens, password hashing, RBAC
│   │
│   ├── db/
│   │   └── base.py              ← Async SQLAlchemy engine + session
│   │
│   ├── models/
│   │   └── ladm.py              ← All 15 ORM models (exact SQL match)
│   │
│   ├── schemas/
│   │   └── ladm.py              ← Pydantic v2 request/response schemas
│   │
│   └── api/routes/
│       ├── auth.py              ← POST /auth/token  POST /auth/register
│       ├── parties.py           ← /parties  /group-parties  /party-members
│       ├── admin.py             ← /baunits  /rrrs  /sources  /admin-sources  /spatial-sources
│       ├── spatial.py           ← /spatial-units  /parcels/geojson  /{su_id}/full-record
│       └── provenance.py        ← /provenance (read-only ETL log)
```

---

## API Endpoint Reference

### Authentication
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/token` | POST | Login — get JWT token |
| `/api/v1/auth/register` | POST | Register new user |

### Party Package
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/parties` | GET | auth | List parties (filter by uz_role, party_type, department) |
| `/api/v1/parties` | POST | admin | Create party |
| `/api/v1/parties/{party_id}` | GET | auth | Get party by ID |
| `/api/v1/parties/{party_id}` | PATCH | admin | Update party |
| `/api/v1/parties/by-role/{role}` | GET | auth | Filter by UZ role |
| `/api/v1/group-parties` | GET | auth | List group parties |
| `/api/v1/group-parties/{group_id}` | GET | auth | Get group party |
| `/api/v1/party-members` | GET | auth | List members (filter by group_id / party_id) |

### Administrative Package
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/baunits` | GET | auth | List BAUnits (filter by unit_type, building_code) |
| `/api/v1/baunits/{baunit_id}` | GET | auth | Get BAUnit |
| `/api/v1/baunits/{baunit_id}/rrrs` | GET | auth | All RRRs for a BAUnit |
| `/api/v1/rrrs` | GET | auth | List RRRs (filter by type, status, rrr_subclass) |
| `/api/v1/rrrs/active` | GET | auth | Active RRRs only |
| `/api/v1/rrrs/{rrr_id}` | GET | auth | Get RRR |
| `/api/v1/admin-sources` | GET | auth | Administrative source documents |
| `/api/v1/spatial-sources` | GET | auth | Spatial source documents |

### Spatial Unit Package — Key GeoBIM Endpoints
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/spatial-units` | GET | auth | List spatial units (attributes only) |
| `/api/v1/spatial-units/{su_id}` | GET | auth | Get spatial unit attributes |
| **`/api/v1/spatial-units/parcels/geojson`** | **GET** | **auth** | **All parcels as GeoJSON FeatureCollection in WGS84 — campus boundary overlay** |
| **`/api/v1/spatial-units/all/geojson`** | **GET** | **auth** | **All spatial units with geometry as GeoJSON (WGS84)** |
| **`/api/v1/spatial-units/{su_id}/geojson`** | **GET** | **auth** | **Single spatial unit GeoJSON Feature (WGS84)** |
| **`/api/v1/spatial-units/{su_id}/full-record`** | **GET** | **auth** | **Full LADM record: geometry + RRRs + party + IFC — primary GeoBIM button endpoint** |
| `/api/v1/bim-mappings` | GET | auth | List IFC GlobalId mappings |
| `/api/v1/bim-mappings/resolve?ifc_id=` | GET | auth | Resolve IFC GlobalId to LADM record |

### Provenance
| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/v1/provenance` | GET | auth | ETL audit log (read-only) |

### System
| Endpoint | Description |
|----------|-------------|
| `/docs` | Swagger UI interactive docs |
| `/redoc` | ReDoc documentation |
| `/health` | Health check |

---

## CRS / Coordinate Reference System

| Layer | SRID | Name | Purpose |
|-------|------|------|---------|
| Stored in PostGIS | **EPSG:20936** | Arc 1960 / UTM Zone 36S | UZ campus surveying CRS — metric, accurate areas |
| Served via API | **EPSG:4326** | WGS84 (lat/lon) | GeoBIM frontend — CesiumJS, Leaflet, Mapbox |

All GeoJSON endpoints use PostGIS `ST_Transform(geom, 4326)` to reproject automatically.

The parcel SU001 (Stand 7777A — 191.75 ha) has the full polygon stored and
will display as the campus boundary in your GeoBIM frontend.

---

## GeoBIM Frontend Integration

### Pattern 1 — Button-based (current approach)

Your colleague assigns each clickable panel/button a `su_id`:

```javascript
// When user clicks a room/building button in the GeoBIM viewer:
async function onSpaceClick(suId) {
  const res = await fetch(`https://your-backend.onrender.com/api/v1/spatial-units/${suId}/full-record`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const record = await res.json();
  // record.geometry_wgs84 → GeoJSON geometry in EPSG:4326
  // record.rrrs           → array of rights/restrictions/responsibilities
  // record.baunit_name    → administrative unit name
  displayInfoPanel(record);
}
```

### Pattern 2 — Campus boundary overlay

```javascript
// Load Stand 7777A boundary on map startup:
const res = await fetch('/api/v1/spatial-units/parcels/geojson', {
  headers: { 'Authorization': `Bearer ${token}` }
});
const geojson = await res.json();
// geojson.features[0].geometry → EPSG:4326 polygon ready for Cesium/Leaflet
map.addLayer(L.geoJSON(geojson));
```

### Pattern 3 — IFC GlobalId resolution (when IFC model matures)

```javascript
// When IFC model has IfcSpace entities:
async function onIFCClick(ifcGlobalId) {
  const res = await fetch(`/api/v1/bim-mappings/resolve?ifc_id=${ifcGlobalId}`, {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const ladmRecord = await res.json();
  // then call full-record with ladmRecord.su_id
}
```

---

## Quick Start (Local Development)

```bash
# 1. Clone your repo
git clone <your-repo-url>
cd ladm_uz_v2

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — add your Supabase DATABASE_URL and SECRET_KEY

# 5. Start server
uvicorn main:app --reload

# 6. Open docs
# http://localhost:8000/docs
```

---

## Deploying to Render

```bash
# 1. Push to GitHub
git add .
git commit -m "v2 - rebuilt on actual SQL schema"
git push origin main

# 2. In Render dashboard:
#    - Go to your Web Service
#    - Click "Manual Deploy" → "Deploy latest commit"
#    - Wait ~2 minutes for build

# 3. Set Environment Variables in Render:
#    DATABASE_URL     = postgresql+asyncpg://postgres.xxxx:pw@...supabase.com:5432/postgres
#    SYNC_DATABASE_URL= postgresql://postgres.xxxx:pw@...supabase.com:5432/postgres
#    SECRET_KEY       = <your-long-random-key>
#    DEBUG            = false
#    ALLOWED_ORIGINS  = https://your-frontend.vercel.app
```

Generate a secure SECRET_KEY:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

---

## Supabase Notes

- Tables are already created from your SQL dump — **do not run `create_all`** in production
- The `lifespan` function in `main.py` has `create_all` commented out — leave it that way
- Geometry column `la_spatialunit.geom` is `geometry(Polygon, 20936)` — correct for your data
- **SU001 (Stand 7777A)** has the full campus polygon stored — test the parcel endpoint first

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `asyncpg.exceptions.TooManyConnectionsError` | Use Supabase connection pooler (Transaction mode, port 6543) |
| `SSL connection required` | Add `?sslmode=require` to DATABASE_URL |
| `geometry type mismatch` | Ensure PostGIS extension is enabled in Supabase (it is by default) |
| `401 Unauthorized` | Add `Authorization: Bearer <token>` header |
| `404 on /parcels/geojson` | Check SU001 has `su_type = 'parcel'` in la_spatialunit |
| `None geometry in response` | SU002–SU017 have no geom yet — only SU001 has the polygon |

---

## RRR Type Reference

| Type | Subclass | Count | Description |
|------|----------|-------|-------------|
| Ownership | LA_Right | 1 | University Council title deed holder |
| Use | LA_Right | 6 | Institutional and personal use rights |
| Occupancy | LA_Right | 3 | Managerial/primary occupancy |
| Maintenance | LA_Responsibility | 2 | Works department duties |
| Admin Support | LA_Responsibility | 1 | Secretary records responsibility |
| Statutory Oversight | LA_Restriction | 1 | DSG boundary restriction |
| Technical | LA_Responsibility | 2 | Lab equipment maintenance |

---

## UZ Role Reference

| uz_role | Prototype parties | Description |
|---------|-------------------|-------------|
| Institution | P001, P002, P003, P011 | UZ, Dept Geomatics, Faculty of Engineering, Dept of Works |
| HOD | P004 | Prof. T. Chikomba |
| ACAD_STAFF | P005, P006 | Dr. Mapuranga, Dr. Mutsvairo |
| ADMIN_STAFF | P007, P012 | Mr. Nyamukondiwa, Secretary |
| TECH_STAFF | P015, P016 | Mrs. Moyo, Mr. Banda |
| STUDENT | P009, P010 | Miss Moyo, Mr. Chizema |
| OWNER | P013 | University Council |
| EXT_AUTH | P014 | Dept Surveyor-General |
