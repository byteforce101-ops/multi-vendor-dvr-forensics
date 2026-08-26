import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

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
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evidence_items: Mapped[list["Evidence"]] = relationship(back_populates="case")

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
    case: Mapped["Case"] = relationship(back_populates="evidence_items")