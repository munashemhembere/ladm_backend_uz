"""
SQLAlchemy ORM models — mapped exactly to your SQL schema.
Tables: app_user, la_party, la_groupparty, la_party_member,
        la_baunit, la_rrr, la_rrr_baunit, la_rrr_admin_source,
        la_source, la_AdministrativeSource, la_SpatialSource,
        la_spatialunit, la_spatialunit_baunit,
        la_spatialunit_ifc_mapping, la_spatialunit_spatial_source,
        la_source_spatialunit, ladm_etl_provenance_log
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Text, Boolean, Date, DateTime,
    Numeric, ForeignKey, BigInteger, UniqueConstraint, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from geoalchemy2 import Geometry
from app.db.base import Base


# ── App User (authentication) ─────────────────────────────────

class AppUser(Base):
    __tablename__ = "app_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="user", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)


# ── Party Package ─────────────────────────────────────────────

class LaParty(Base):
    __tablename__ = "la_party"

    party_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    party_type: Mapped[Optional[str]] = mapped_column(Text)
    # CHECK: naturalPerson | nonNaturalPerson
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    uz_role: Mapped[Optional[str]] = mapped_column(Text)
    ext_id: Mapped[Optional[str]] = mapped_column(Text)
    email: Mapped[Optional[str]] = mapped_column(Text)
    department: Mapped[Optional[str]] = mapped_column(Text)
    is_active: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    gender: Mapped[Optional[str]] = mapped_column(Text)
    party_ext_type: Mapped[Optional[str]] = mapped_column(Text)

    rrrs: Mapped[List["LaRRR"]] = relationship("LaRRR", back_populates="party")
    group_memberships: Mapped[List["LaPartyMember"]] = relationship(
        "LaPartyMember", back_populates="party", foreign_keys="LaPartyMember.party_id"
    )


class LaGroupParty(Base):
    __tablename__ = "la_groupparty"

    group_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    group_type: Mapped[Optional[str]] = mapped_column(Text)
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    members: Mapped[List["LaPartyMember"]] = relationship(
        "LaPartyMember", back_populates="group_party"
    )


class LaPartyMember(Base):
    __tablename__ = "la_party_member"
    __table_args__ = (
        UniqueConstraint("group_id", "party_id", "begin_lifespan_version"),
    )

    member_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    group_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("la_groupparty.group_id", ondelete="CASCADE"), nullable=False
    )
    party_id: Mapped[str] = mapped_column(
        String(20), ForeignKey("la_party.party_id", ondelete="CASCADE"), nullable=False
    )
    role_in_group: Mapped[Optional[str]] = mapped_column(Text)
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    group_party: Mapped["LaGroupParty"] = relationship("LaGroupParty", back_populates="members")
    party: Mapped["LaParty"] = relationship(
        "LaParty", back_populates="group_memberships", foreign_keys=[party_id]
    )


# ── Administrative Package ────────────────────────────────────

class LaBaunit(Base):
    __tablename__ = "la_baunit"

    baunit_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[Optional[str]] = mapped_column(Text, default="basicUnit")
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    unit_type: Mapped[Optional[str]] = mapped_column(Text)
    building_code: Mapped[Optional[str]] = mapped_column(String(50))
    description: Mapped[Optional[str]] = mapped_column(Text)

    rrrs: Mapped[List["LaRRR"]] = relationship("LaRRR", back_populates="baunit")
    spatial_units: Mapped[List["LaSpatialUnit"]] = relationship(
        "LaSpatialUnit", back_populates="baunit"
    )
    rrr_baunit_links: Mapped[List["LaRRRBaunit"]] = relationship(
        "LaRRRBaunit", back_populates="baunit"
    )
    spatialunit_baunit_links: Mapped[List["LaSpatialUnitBaunit"]] = relationship(
        "LaSpatialUnitBaunit", back_populates="baunit"
    )


class LaRRR(Base):
    __tablename__ = "la_rrr"

    rrr_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    type: Mapped[Optional[str]] = mapped_column(Text)
    # CHECK: Ownership|Use|Occupancy|Maintenance|Admin Support|
    #        Statutory Oversight|Institutional|Technical
    party_id: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("la_party.party_id")
    )
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    status: Mapped[Optional[str]] = mapped_column(String(20))
    baunit_id: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("la_baunit.baunit_id")
    )
    rrr_subclass: Mapped[Optional[str]] = mapped_column(String(50))
    # LA_Right | LA_Restriction | LA_Responsibility
    description: Mapped[Optional[str]] = mapped_column(Text)

    party: Mapped[Optional["LaParty"]] = relationship("LaParty", back_populates="rrrs")
    baunit: Mapped[Optional["LaBaunit"]] = relationship("LaBaunit", back_populates="rrrs")
    rrr_baunit_links: Mapped[List["LaRRRBaunit"]] = relationship(
        "LaRRRBaunit", back_populates="rrr"
    )
    admin_source_links: Mapped[List["LaRRRAdminSource"]] = relationship(
        "LaRRRAdminSource", back_populates="rrr"
    )


class LaRRRBaunit(Base):
    """Many-to-many: la_rrr <-> la_baunit"""
    __tablename__ = "la_rrr_baunit"

    rrr_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("la_rrr.rrr_id"), primary_key=True
    )
    baunit_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("la_baunit.baunit_id"), primary_key=True
    )

    rrr: Mapped["LaRRR"] = relationship("LaRRR", back_populates="rrr_baunit_links")
    baunit: Mapped["LaBaunit"] = relationship("LaBaunit", back_populates="rrr_baunit_links")


class LaRRRAdminSource(Base):
    """Many-to-many: la_rrr <-> la_AdministrativeSource"""
    __tablename__ = "la_rrr_admin_source"

    rrr_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("la_rrr.rrr_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    source_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("la_AdministrativeSource.source_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )

    rrr: Mapped["LaRRR"] = relationship("LaRRR", back_populates="admin_source_links")
    admin_source: Mapped["LaAdministrativeSource"] = relationship(
        "LaAdministrativeSource", back_populates="rrr_links"
    )


# ── Source / Surveying Package ────────────────────────────────

class LaSource(Base):
    __tablename__ = "la_source"

    source_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    type: Mapped[Optional[str]] = mapped_column(Text)
    # CHECK: AdministrativeSource | SpatialSource
    description: Mapped[Optional[str]] = mapped_column(Text)
    begin_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    spatialunit_links: Mapped[List["LaSourceSpatialUnit"]] = relationship(
        "LaSourceSpatialUnit", back_populates="source"
    )


class LaAdministrativeSource(Base):
    __tablename__ = "la_AdministrativeSource"

    source_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    official_identifier: Mapped[Optional[str]] = mapped_column(String(100))
    acceptance_date: Mapped[Optional[date]] = mapped_column(Date)
    ext_archive_id: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    begin_lifespan_version: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    rrr_links: Mapped[List["LaRRRAdminSource"]] = relationship(
        "LaRRRAdminSource", back_populates="admin_source"
    )


class LaSpatialSource(Base):
    __tablename__ = "la_SpatialSource"

    source_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    official_identifier: Mapped[Optional[str]] = mapped_column(String(100))
    acceptance_date: Mapped[Optional[date]] = mapped_column(Date)
    ext_archive_id: Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    begin_lifespan_version: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    spatialunit_links: Mapped[List["LaSpatialUnitSpatialSource"]] = relationship(
        "LaSpatialUnitSpatialSource", back_populates="spatial_source"
    )


class LaSourceSpatialUnit(Base):
    """la_source_spatialunit join table"""
    __tablename__ = "la_source_spatialunit"

    source_id: Mapped[str] = mapped_column(
        String(10), ForeignKey("la_source.source_id"), primary_key=True
    )
    uid: Mapped[str] = mapped_column(
        String(10), ForeignKey("la_spatialunit.su_id"), primary_key=True
    )

    source: Mapped["LaSource"] = relationship("LaSource", back_populates="spatialunit_links")
    spatial_unit: Mapped["LaSpatialUnit"] = relationship(
        "LaSpatialUnit", back_populates="source_links"
    )


# ── Spatial Unit Package ──────────────────────────────────────

class LaSpatialUnit(Base):
    __tablename__ = "la_spatialunit"

    su_id: Mapped[str] = mapped_column(String(10), primary_key=True)
    baunit_id: Mapped[Optional[str]] = mapped_column(
        String(10), ForeignKey("la_baunit.baunit_id")
    )
    global_id_ifc: Mapped[Optional[str]] = mapped_column(String(22))
    label: Mapped[Optional[str]] = mapped_column(Text)
    su_type: Mapped[Optional[str]] = mapped_column(Text)
    # parcel | building | room
    area_m2: Mapped[Optional[float]] = mapped_column(Numeric)
    capacity: Mapped[Optional[int]] = mapped_column(Integer)
    surface_relation: Mapped[Optional[str]] = mapped_column(Text)
    dimension: Mapped[Optional[str]] = mapped_column(String(10), nullable=True) # <-- ADDED: Matches your new 2D/3D column
    
    # PostGIS geometry — stored in EPSG:20936
    geom: Mapped[Optional[object]] = mapped_column(
        Geometry("POLYGON", srid=20936), nullable=True
    )

    baunit: Mapped[Optional["LaBaunit"]] = relationship(
        "LaBaunit", back_populates="spatial_units"
    )
    ifc_mappings: Mapped[List["LaSpatialUnitIFCMapping"]] = relationship(
        "LaSpatialUnitIFCMapping", back_populates="spatial_unit",
        cascade="all, delete-orphan"
    )
    spatialunit_baunit_links: Mapped[List["LaSpatialUnitBaunit"]] = relationship(
        "LaSpatialUnitBaunit", back_populates="spatial_unit",
        cascade="all, delete-orphan"
    )
    spatial_source_links: Mapped[List["LaSpatialUnitSpatialSource"]] = relationship(
        "LaSpatialUnitSpatialSource", back_populates="spatial_unit",
        cascade="all, delete-orphan"
    )
    source_links: Mapped[List["LaSourceSpatialUnit"]] = relationship(
        "LaSourceSpatialUnit", back_populates="spatial_unit"
    )


class LaSpatialUnitBaunit(Base):
    """Many-to-many: la_spatialunit <-> la_baunit (with lifespan)"""
    __tablename__ = "la_spatialunit_baunit"

    su_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("la_spatialunit.su_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    baunit_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("la_baunit.baunit_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    begin_lifespan_version: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    end_lifespan_version: Mapped[Optional[datetime]] = mapped_column(DateTime)

    spatial_unit: Mapped["LaSpatialUnit"] = relationship(
        "LaSpatialUnit", back_populates="spatialunit_baunit_links"
    )
    baunit: Mapped["LaBaunit"] = relationship(
        "LaBaunit", back_populates="spatialunit_baunit_links"
    )


class LaSpatialUnitIFCMapping(Base):
    """LADM SpatialUnit <--> IFC GlobalId bridge"""
    __tablename__ = "la_spatialunit_ifc_mapping"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    spatial_unit_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("la_spatialunit.su_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False
    )
    ifc_global_id: Mapped[Optional[str]] = mapped_column(String(22), nullable=True) # <-- UPDATED: Allows NULL rows in bridge tables
    ifc_entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ifc_name: Mapped[Optional[str]] = mapped_column(String(255))
    ifc_source_file: Mapped[Optional[str]] = mapped_column(String(500))
    mapped_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    mapped_by: Mapped[Optional[str]] = mapped_column(String(100))

    spatial_unit: Mapped["LaSpatialUnit"] = relationship(
        "LaSpatialUnit", back_populates="ifc_mappings"
    )


class LaSpatialUnitSpatialSource(Base):
    """la_spatialunit_spatial_source join table"""
    __tablename__ = "la_spatialunit_spatial_source"

    su_id: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("la_spatialunit.su_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )
    source_id: Mapped[str] = mapped_column(
        String(20),
        ForeignKey("la_SpatialSource.source_id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True
    )

    spatial_unit: Mapped["LaSpatialUnit"] = relationship(
        "LaSpatialUnit", back_populates="spatial_source_links"
    )
    spatial_source: Mapped["LaSpatialSource"] = relationship(
        "LaSpatialSource", back_populates="spatialunit_links"
    )


# ── ETL Provenance Log ────────────────────────────────────────

class LadmEtlProvenanceLog(Base):
    __tablename__ = "ladm_etl_provenance_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    operation: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(10), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    source_file: Mapped[Optional[str]] = mapped_column(String(500))
    target_table: Mapped[Optional[str]] = mapped_column(String(100))
    records_affected: Mapped[int] = mapped_column(Integer, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text)
    script_name: Mapped[Optional[str]] = mapped_column(String(200))
    executed_by: Mapped[Optional[str]] = mapped_column(String(100))