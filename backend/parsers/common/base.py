from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ParseError(str, Enum):
    UNSUPPORTED_VENDOR = "UNSUPPORTED_VENDOR"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    CORRUPTED_EVIDENCE = "CORRUPTED_EVIDENCE"
    PARTIALLY_PARSED = "PARTIALLY_PARSED"
    PARSE_FAILED = "PARSE_FAILED"
    EXTRACTION_FAILED = "EXTRACTION_FAILED"


@dataclass
class NormalizedRecording:
    camera_id: str
    recording_id: str
    source_path: str
    extracted_path: str | None
    original_timestamp: datetime | None
    normalized_timestamp: datetime | None
    duration_seconds: float | None
    resolution: str | None
    fps: float | None
    codec: str | None
    file_size: int | None
    recovery_status: str  # "ORIGINAL" | "RECOVERED" | "PARTIAL"
    device_model: str | None = None
    raw_metadata: dict = field(default_factory=dict)


@dataclass
class ParseResult:
    vendor: str
    parser_version: str
    success: bool
    recordings: list[NormalizedRecording] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    error_code: ParseError | None = None
    raw_master_block: object | None = None


class BaseDVRParser(ABC):
    vendor_name: str
    parser_version: str = "0.1.0"

    @abstractmethod
    def detect(self, evidence_path: str) -> tuple[bool, float, dict]:
        """Return (is_match, confidence 0-1, device_info dict). Must not raise
        on non-matching input — return (False, 0.0, {})."""
        ...

    @abstractmethod
    def validate(self, evidence_path: str) -> tuple[bool, list[str]]:
        """Return (is_valid, warnings). Checked version drift goes here as a warning,
        not a hard failure."""
        ...

    @abstractmethod
    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        ...

    def get_parser_info(self) -> dict:
        return {"vendor": self.vendor_name, "version": self.parser_version}