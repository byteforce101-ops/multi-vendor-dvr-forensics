import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class EvidenceStatus(str, enum.Enum):
    ACQUIRED = "acquired"
    HASHED = "hashed"
    VERIFIED = "verified"
    TAMPERED = "tampered"

class Case(Base):
    __tablename__ = "cases"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String)
    investigator: Mapped[str] = mapped_column(String)
    case_number: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="open")
    # Supabase auth.users.id. It is stored as a plain UUID/string because the
    # auth schema is owned by Supabase and is not part of this application's ORM.
    owner_auth_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="case", cascade="all, delete-orphan")

class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("cases.id"))
    original_filename: Mapped[str] = mapped_column(String)
    original_path: Mapped[str] = mapped_column(String)      # read-only reference, never written to
    working_copy_path: Mapped[str] = mapped_column(String)  # actual file operated on
    sha256: Mapped[str] = mapped_column(String, nullable=True)
    md5: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[EvidenceStatus] = mapped_column(Enum(EvidenceStatus), default=EvidenceStatus.ACQUIRED)
    acquired_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    vendor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    parser_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    parse_warnings: Mapped[list[str]] = mapped_column(JSON, default=list)
    parse_errors: Mapped[list[str]] = mapped_column(JSON, default=list)
    case: Mapped["Case"] = relationship(back_populates="evidence_items")
    devices: Mapped[list["Device"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="evidence", cascade="all, delete-orphan")


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (UniqueConstraint("evidence_id", "vendor", name="uq_device_evidence_vendor"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), index=True)
    vendor: Mapped[str] = mapped_column(String(100), index=True)
    model: Mapped[str | None] = mapped_column(String(255), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(255), nullable=True)
    firmware_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped["Evidence"] = relationship(back_populates="devices")
    recordings: Mapped[list["Recording"]] = relationship(back_populates="device")


class Recording(Base):
    __tablename__ = "recordings"
    __table_args__ = (UniqueConstraint("evidence_id", "recording_identifier", name="uq_recording_evidence_identifier"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id"), index=True)
    device_id: Mapped[str | None] = mapped_column(ForeignKey("devices.id"), index=True, nullable=True)
    camera_id: Mapped[str] = mapped_column(String(100), index=True)
    recording_identifier: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(Text)
    extracted_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    original_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    normalized_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    codec: Mapped[str | None] = mapped_column(String(100), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recovery_status: Mapped[str] = mapped_column(String(50))
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    evidence: Mapped["Evidence"] = relationship(back_populates="recordings")
    device: Mapped["Device | None"] = relationship(back_populates="recordings")
