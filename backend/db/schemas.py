from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CaseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    investigator: str = Field(min_length=1, max_length=255)
    case_number: str | None = Field(default=None, max_length=100)
    description: str | None = None


class EvidenceCreate(BaseModel):
    source_path: str = Field(min_length=1)


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    vendor: str
    model: str | None
    serial_number: str | None
    firmware_version: str | None
    raw_metadata: dict[str, Any]


class RecordingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    camera_id: str
    recording_identifier: str
    source_path: str
    extracted_path: str | None
    original_timestamp: datetime | None
    normalized_timestamp: datetime | None
    duration_seconds: float | None
    resolution: str | None
    fps: float | None
    codec: str | None
    file_size: int | None
    recovery_status: str
    raw_metadata: dict[str, Any]


class EvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    case_id: str
    original_filename: str
    original_path: str
    working_copy_path: str
    sha256: str | None
    md5: str | None
    status: str
    acquired_at: datetime
    vendor: str | None
    parser_version: str | None
    parse_warnings: list[str]
    parse_errors: list[str]
    devices: list[DeviceRead] = []
    recordings: list[RecordingRead] = []


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    investigator: str
    case_number: str | None
    description: str | None
    status: str
    created_at: datetime
