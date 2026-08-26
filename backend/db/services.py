"""Translate parser dataclasses into persistence records.

This is the only layer allowed to know both ParseResult and SQLAlchemy models.
"""

from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.db.models import Device, Evidence, Recording
from backend.parsers.common.base import ParseResult


def _json_safe(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return _json_safe(dataclasses.asdict(value))
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def persist_parse_result(
    db: Session,
    evidence: Evidence,
    result: ParseResult,
    device_info: dict[str, Any] | None = None,
) -> tuple[Device | None, list[Recording]]:
    """Persist a ParseResult idempotently; parsers themselves remain ORM-free."""
    evidence.vendor = result.vendor
    evidence.parser_version = result.parser_version
    evidence.parse_warnings = _json_safe(result.warnings)
    evidence.parse_errors = _json_safe(result.errors)
    if not result.success:
        db.commit()
        return None, []

    info = device_info or {}
    device = db.query(Device).filter(
        Device.evidence_id == evidence.id, Device.vendor == result.vendor
    ).one_or_none()
    if device is None:
        device = Device(evidence_id=evidence.id, vendor=result.vendor)
        db.add(device)
    device.model = info.get("model") or next(
        (recording.device_model for recording in result.recordings if recording.device_model), None
    )
    device.serial_number = info.get("serial_number")
    device.firmware_version = info.get("version") or info.get("firmware_version")
    device.raw_metadata = _json_safe(info)
    db.flush()

    stored: list[Recording] = []
    for parsed in result.recordings:
        recording = db.query(Recording).filter(
            Recording.evidence_id == evidence.id,
            Recording.recording_identifier == parsed.recording_id,
        ).one_or_none()
        if recording is None:
            recording = Recording(
                evidence_id=evidence.id,
                device_id=device.id,
                recording_identifier=parsed.recording_id,
                camera_id=parsed.camera_id,
                source_path=parsed.source_path,
                recovery_status=parsed.recovery_status,
            )
            db.add(recording)
        recording.device_id = device.id
        recording.camera_id = parsed.camera_id
        recording.source_path = parsed.source_path
        recording.extracted_path = parsed.extracted_path
        recording.original_timestamp = parsed.original_timestamp
        recording.normalized_timestamp = parsed.normalized_timestamp
        recording.duration_seconds = parsed.duration_seconds
        recording.resolution = parsed.resolution
        recording.fps = parsed.fps
        recording.codec = parsed.codec
        recording.file_size = parsed.file_size
        recording.recovery_status = parsed.recovery_status
        recording.raw_metadata = _json_safe(parsed.raw_metadata)
        stored.append(recording)

    db.commit()
    for recording in stored:
        db.refresh(recording)
    return device, stored
