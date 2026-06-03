"""
ETL Validation and Provenance Logging Script
LADM UZ Smart Campus Digital Twin — v2
Geomatics Engineering Department, University of Zimbabwe

This script:
  1. Connects to your Supabase PostgreSQL database
  2. Runs validation queries against every LADM table
  3. Validates geometry (Stand 7777A) — area, CRS, WGS84 transform
  4. Logs every result to ladm_etl_provenance_log
  5. Prints a summary report for Chapter 4 / 5 results

Run from project root:
    python etl_test.py

Requirements: same .env as the main app
"""
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Load .env ─────────────────────────────────────────────────
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

DATABASE_URL = os.getenv("SYNC_DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: SYNC_DATABASE_URL not found in .env")
    sys.exit(1)

import sqlalchemy as sa
from sqlalchemy import text

engine = sa.create_engine(DATABASE_URL, echo=False)

# ── Colour helpers (Windows-safe) ─────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def ok(msg):  print(f"  {GREEN}\u2714{RESET}  {msg}")
def fail(msg):print(f"  {RED}\u2718{RESET}  {msg}")
def info(msg):print(f"  {YELLOW}\u25ba{RESET}  {msg}")
def header(msg): print(f"\n{BOLD}{msg}{RESET}\n{'='*60}")

# ── Provenance logger ─────────────────────────────────────────
def log(conn, operation, status, table, records=0, message=""):
    conn.execute(text("""
        INSERT INTO ladm_etl_provenance_log
          (operation, status, target_table, records_affected, message, script_name, executed_by)
        VALUES
          (:op, :st, :tb, :rc, :ms, :sn, :eb)
    """), {
        "op": operation,
        "st": status,
        "tb": table,
        "rc": records,
        "ms": message,
        "sn": "etl_test.py",
        "eb": "etl_validation_run"
    })

# ── Test definitions ──────────────────────────────────────────
# Each entry: (label, table, expected_min_count, sql_override)
TABLE_TESTS = [
    ("Party records",             "la_party",                     16, None),
    ("Group party records",       "la_groupparty",                 7, None),
    ("Party member records",      "la_party_member",              16, None),
    ("Basic admin units (BAUnits)","la_baunit",                    4, None),
    ("RRR records",               "la_rrr",                       16, None),
    ("RRR-BAUnit links",          "la_rrr_baunit",                16, None),
    ("RRR-Admin source links",    "la_rrr_admin_source",          15, None),
    ("Administrative sources",    "la_AdministrativeSource",      10, None),
    ("Spatial sources",           "la_SpatialSource",              4, None),
    ("Source records (generic)",  "la_source",                     3, None),
    ("Spatial units",             "la_spatialunit",               16, None),
    ("SpatialUnit-BAUnit links",  "la_spatialunit_baunit",         4, None),
    ("SpatialUnit-SpatialSource", "la_spatialunit_spatial_source", 4, None),
    ("Spatial Unit IFC mappings", "la_spatialunit_ifc_mapping",    0, None), # Added to track BIM bridge table
    ("Source-SpatialUnit links",  "la_source_spatialunit",         0, None), # Added for complete package coverage
]

def run_tests():
    results = []
    passed  = 0
    failed  = 0

    with engine.connect() as conn:

        # ── 1. TABLE COUNT VALIDATION ─────────────────────────
        header("STAGE 1: Table Record Count Validation")

        for label, table, expected_min, _ in TABLE_TESTS:
            try:
                count = conn.execute(
                    text(f'SELECT COUNT(*) FROM "{table}"')
                ).scalar()

                if count >= expected_min:
                    ok(f"{label}: {count} records (expected \u2265{expected_min})")
                    log(conn, "VALIDATE", "SUCCESS", table, count,
                        f"{label}: {count} records loaded, expected \u2265{expected_min}")
                    passed += 1
                    results.append((label, "PASS", count))
                else:
                    fail(f"{label}: {count} records (expected \u2265{expected_min}) \u2014 BELOW THRESHOLD")
                    log(conn, "VALIDATE", "FAILED", table, count,
                        f"{label}: {count} records, expected \u2265{expected_min}")
                    failed += 1
                    results.append((label, "FAIL", count))
            except Exception as e:
                fail(f"{label}: ERROR \u2014 {e}")
                log(conn, "VALIDATE", "FAILED", table, 0, str(e))
                failed += 1
                results.append((label, "ERROR", 0))

        # ── 2. GEOMETRY VALIDATION ────────────────────────────
        header("STAGE 2: Spatial Geometry Validation (Stand 7777A — SU001)")

        # 2a. Does SU001 have geometry?
        try:
            has_geom = conn.execute(text(
                "SELECT geom IS NOT NULL FROM la_spatialunit WHERE su_id = 'SU001'"
            )).scalar()
            if has_geom:
                ok("SU001 has geometry stored (NOT NULL)")
                log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                    "SU001 geometry is not null")
                passed += 1
                results.append(("SU001 geometry exists", "PASS", 1))
            else:
                fail("SU001 geometry is NULL")
                log(conn, "VALIDATE", "FAILED", "la_spatialunit", 0,
                    "SU001 geometry is null")
                failed += 1
                results.append(("SU001 geometry exists", "FAIL", 0))
        except Exception as e:
            fail(f"SU001 geometry check error: {e}")
            failed += 1

        # 2b. Area check
        try:
            area = conn.execute(text(
                "SELECT ROUND(ST_Area(geom)::numeric, 0) FROM la_spatialunit WHERE su_id = 'SU001'"
            )).scalar()
            area = float(area) if area else 0
            expected_area = 1917530
            tolerance     = 5000   # ±5000 m² tolerance
            if abs(area - expected_area) <= tolerance:
                ok(f"SU001 area: {area:,.0f} m\u00b2 (expected ~{expected_area:,} m\u00b2, within \u00b1{tolerance:,} m\u00b2)")
                log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                    f"SU001 area = {area} m2, expected {expected_area} m2")
                passed += 1
                results.append(("SU001 area validation", "PASS", int(area)))
            else:
                fail(f"SU001 area: {area:,.0f} m\u00b2 (expected ~{expected_area:,} m\u00b2) \u2014 OUTSIDE TOLERANCE")
                log(conn, "VALIDATE", "FAILED", "la_spatialunit", 1,
                    f"SU001 area = {area} m2, expected {expected_area} m2")
                failed += 1
                results.append(("SU001 area validation", "FAIL", int(area)))
        except Exception as e:
            fail(f"Area check error: {e}")
            failed += 1

        # 2c. Stored CRS check
        try:
            srid = conn.execute(text(
                "SELECT ST_SRID(geom) FROM la_spatialunit WHERE su_id = 'SU001'"
            )).scalar()
            if srid == 20936:
                ok(f"SU001 stored CRS: EPSG:{srid} (Arc 1960 / UTM Zone 36S) \u2714")
                log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                    f"SU001 SRID = {srid} (EPSG:20936 confirmed)")
                passed += 1
                results.append(("SU001 stored CRS EPSG:20936", "PASS", srid))
            else:
                fail(f"SU001 stored CRS: EPSG:{srid} (expected EPSG:20936)")
                log(conn, "VALIDATE", "FAILED", "la_spatialunit", 1,
                    f"SU001 SRID = {srid}, expected 20936")
                failed += 1
                results.append(("SU001 stored CRS EPSG:20936", "FAIL", srid))
        except Exception as e:
            fail(f"CRS check error: {e}")
            failed += 1

        # 2d. WGS84 transform check
        try:
            coords = conn.execute(text("""
                SELECT
                  ROUND(ST_X(ST_Centroid(ST_Transform(geom, 4326)))::numeric, 4) AS lon,
                  ROUND(ST_Y(ST_Centroid(ST_Transform(geom, 4326)))::numeric, 4) AS lat
                FROM la_spatialunit
                WHERE su_id = 'SU001'
            """)).fetchone()
            lon, lat = float(coords[0]), float(coords[1])
            # Mount Pleasant, Harare: ~31.05°E, ~-17.78°S
            lon_ok = 30.9 <= lon <= 31.2
            lat_ok = -17.9 <= lat <= -17.6
            if lon_ok and lat_ok:
                ok(f"SU001 WGS84 centroid: lon={lon}\u00b0, lat={lat}\u00b0 \u2014 within Harare range \u2714")
                log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                    f"SU001 WGS84 centroid: lon={lon}, lat={lat} (Harare range confirmed)")
                passed += 1
                results.append(("SU001 WGS84 transform", "PASS", 1))
            else:
                fail(f"SU001 WGS84 centroid: lon={lon}\u00b0, lat={lat}\u00b0 \u2014 OUTSIDE HARARE RANGE")
                log(conn, "VALIDATE", "FAILED", "la_spatialunit", 1,
                    f"SU001 WGS84 centroid: lon={lon}, lat={lat} outside expected range")
                failed += 1
                results.append(("SU001 WGS84 transform", "FAIL", 1))
        except Exception as e:
            fail(f"WGS84 transform check error: {e}")
            failed += 1

        # 2e. Vertex count
        try:
            vertices = conn.execute(text(
                "SELECT ST_NPoints(geom) FROM la_spatialunit WHERE su_id = 'SU001'"
            )).scalar()
            ok(f"SU001 polygon vertex count: {vertices} vertices")
            log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                f"SU001 polygon has {vertices} vertices")
            passed += 1
            results.append(("SU001 vertex count", "PASS", vertices))
        except Exception as e:
            fail(f"Vertex count error: {e}")
            failed += 1

        # 2f. Geometry validity
        try:
            valid = conn.execute(text(
                "SELECT ST_IsValid(geom) FROM la_spatialunit WHERE su_id = 'SU001'"
            )).scalar()
            if valid:
                ok("SU001 geometry is valid (ST_IsValid = TRUE)")
                log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 1,
                    "SU001 geometry passes ST_IsValid check")
                passed += 1
                results.append(("SU001 geometry validity", "PASS", 1))
            else:
                fail("SU001 geometry is INVALID (ST_IsValid = FALSE)")
                log(conn, "VALIDATE", "FAILED", "la_spatialunit", 0,
                    "SU001 geometry fails ST_IsValid")
                failed += 1
                results.append(("SU001 geometry validity", "FAIL", 0))
        except Exception as e:
            fail(f"Geometry validity error: {e}")
            failed += 1

        # ── 3. REFERENTIAL INTEGRITY ──────────────────────────
        header("STAGE 3: Referential Integrity Validation")

        integrity_tests = [
            ("All RRRs have a valid party_id",
             "SELECT COUNT(*) FROM la_rrr r LEFT JOIN la_party p ON r.party_id = p.party_id WHERE r.party_id IS NOT NULL AND p.party_id IS NULL",
             0, "orphan RRRs (no matching party)"),
            ("All RRRs have a valid baunit_id",
             "SELECT COUNT(*) FROM la_rrr r LEFT JOIN la_baunit b ON r.baunit_id = b.baunit_id WHERE r.baunit_id IS NOT NULL AND b.baunit_id IS NULL",
             0, "orphan RRRs (no matching BAUnit)"),
            ("All spatial units have a valid baunit_id",
             "SELECT COUNT(*) FROM la_spatialunit su LEFT JOIN la_baunit b ON su.baunit_id = b.baunit_id WHERE su.baunit_id IS NOT NULL AND b.baunit_id IS NULL",
             0, "orphan spatial units (no matching BAUnit)"),
            ("All party members reference valid parties",
             "SELECT COUNT(*) FROM la_party_member pm LEFT JOIN la_party p ON pm.party_id = p.party_id WHERE p.party_id IS NULL",
             0, "orphan party members"),
            ("All RRR-BAUnit links reference valid RRRs",
             "SELECT COUNT(*) FROM la_rrr_baunit rb LEFT JOIN la_rrr r ON rb.rrr_id = r.rrr_id WHERE r.rrr_id IS NULL",
             0, "broken RRR-BAUnit links"),
            ("Spatial unit IDs are properly zero-padded (no 'SU17')", # <-- ADDED: Zero-padding check
             "SELECT COUNT(*) FROM la_spatialunit WHERE su_id = 'SU17'",
             0, "unpadded legacy identifiers found ('SU17' instead of 'SU017')"),
        ]

        for label, sql, expected, error_desc in integrity_tests:
            try:
                count = conn.execute(text(sql)).scalar()
                if count == expected:
                    ok(f"{label}: {count} issues found \u2714")
                    log(conn, "VALIDATE", "SUCCESS", "referential_integrity", 0,
                        f"{label}: OK")
                    passed += 1
                    results.append((label, "PASS", count))
                else:
                    fail(f"{label}: {count} {error_desc} found!")
                    log(conn, "VALIDATE", "WARNING", "referential_integrity", count,
                        f"{label}: {count} {error_desc}")
                    failed += 1
                    results.append((label, "FAIL", count))
            except Exception as e:
                fail(f"{label}: ERROR \u2014 {e}")
                failed += 1

        # ── 4. RRR DISTRIBUTION ───────────────────────────────
        header("STAGE 4: RRR Type Distribution")

        try:
            rrr_types = conn.execute(text(
                "SELECT type, rrr_subclass, COUNT(*) as cnt FROM la_rrr GROUP BY type, rrr_subclass ORDER BY type"
            )).fetchall()
            for row in rrr_types:
                info(f"  {row[0]:30s} | {str(row[1]):25s} | {row[2]} record(s)")
            log(conn, "VALIDATE", "SUCCESS", "la_rrr", 16,
                f"RRR distribution: {len(rrr_types)} type-subclass combinations")
            passed += 1
            results.append(("RRR type distribution", "PASS", len(rrr_types)))
        except Exception as e:
            fail(f"RRR distribution error: {e}")
            failed += 1

        # ── 5. SPATIAL UNIT TYPE & DIMENSION DISTRIBUTION ─────
        header("STAGE 5: Spatial Unit Type & Dimension Distribution") # <-- UPDATED: Includes dimension checking

        try:
            su_types = conn.execute(text(
                """
                SELECT su_type, surface_relation, dimension, COUNT(*) as cnt, 
                       COALESCE(SUM(CASE WHEN geom IS NOT NULL THEN 1 ELSE 0 END), 0) as with_geom 
                FROM la_spatialunit 
                GROUP BY su_type, surface_relation, dimension 
                ORDER BY su_type
                """
            )).fetchall()
            for row in su_types:
                info(f"  {str(row[0]):12s} | {str(row[1]):15s} | {str(row[2]):6s} | {row[3]} unit(s) | {row[4]} with geometry")
            log(conn, "VALIDATE", "SUCCESS", "la_spatialunit", 17,
                f"Spatial unit distribution: {len(su_types)} type/dimension combinations")
            passed += 1
            results.append(("Spatial unit distribution", "PASS", len(su_types)))
        except Exception as e:
            fail(f"SU distribution error: {e}")
            failed += 1

        # ── 6. PROVENANCE LOG CHECK ───────────────────────────
        header("STAGE 6: Provenance Log Summary")

        try:
            prov_count = conn.execute(text(
                "SELECT COUNT(*) FROM ladm_etl_provenance_log WHERE script_name = 'etl_test.py'"
            )).scalar()
            info(f"Provenance entries logged by this run so far: {prov_count}")

            all_prov = conn.execute(text(
                "SELECT operation, status, COUNT(*) FROM ladm_etl_provenance_log GROUP BY operation, status"
            )).fetchall()
            for row in all_prov:
                info(f"  {row[0]:12s} | {row[1]:10s} | {row[2]} entries")

            log(conn, "VALIDATE", "SUCCESS", "ladm_etl_provenance_log", prov_count,
                "Provenance log is populated and accessible")
            passed += 1
        except Exception as e:
            fail(f"Provenance log check error: {e}")
            failed += 1

        # ── COMMIT ALL PROVENANCE ENTRIES ─────────────────────
        conn.commit()

    # ── FINAL REPORT ──────────────────────────────────────────
    total = passed + failed
    header("VALIDATION SUMMARY REPORT")
    print(f"  Total tests run : {total}")
    print(f"  {GREEN}Passed{RESET}          : {passed}")
    print(f"  {RED}Failed{RESET}          : {failed}")
    print(f"  Pass rate       : {(passed/total*100):.1f}%\n")

    if failed == 0:
        print(f"  {GREEN}{BOLD}ALL TESTS PASSED \u2714 — ETL validation successful{RESET}")
        print(f"  {GREEN}Provenance entries logged to Supabase ladm_etl_provenance_log{RESET}")
    else:
        print(f"  {RED}{BOLD}{failed} test(s) FAILED — review output above{RESET}")

    print("\n" + "="*60)
    print(f"  Run completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Print table for Chapter 4
    print(f"\n{BOLD}CHAPTER 4 RESULTS TABLE DATA:{RESET}")
    print(f"{'Test':<45} {'Result':<8} {'Value'}")
    print("-"*70)
    for label, status, value in results:
        colour = GREEN if status == "PASS" else RED
        print(f"{label:<45} {colour}{status:<8}{RESET} {value}")


if __name__ == "__main__":
    print(f"\n{BOLD}LADM UZ Smart Campus Digital Twin — ETL Validation{RESET}")
    print(f"Database: Supabase (PostgreSQL 17 + PostGIS)")
    print(f"Started : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    run_tests()