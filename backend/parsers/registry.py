"""
ParserManager: detects which vendor parser applies to a given evidence file
and dispatches to it. New vendors register themselves in PARSERS below —
nothing else in the app should need to change to add one.
"""

from pathlib import Path
from backend.parsers.common.base import BaseDVRParser, ParseResult, ParseError
from backend.parsers.hikvision.parser import HikvisionParser
from backend.parsers.heimvision.parser import HeimVisionParser
from backend.parsers.carver.parser import ForensicDiskCarverParser
from backend.parsers.generic.parser import GenericVideoParser

# Order matters: more specific/proprietary parsers should be tried before
# disk carvers and generic fallbacks.
PARSERS: list[BaseDVRParser] = [
    HikvisionParser(),
    HeimVisionParser(),
    ForensicDiskCarverParser(),
    GenericVideoParser(),
]

SPLIT_OR_CONTAINER_EXTS = {".e01", ".ex01", ".001"}


class ParserManager:
    def detect_candidates(
        self, evidence_path: str, exhaustive: bool = False
    ) -> tuple[BaseDVRParser | None, float, dict, list[dict]]:
        """Try each registered parser's detect(); return best match and all candidate evaluations."""
        best_parser, best_confidence, best_info = None, 0.0, {}
        candidates: list[dict] = []

        for parser in PARSERS:
            if not exhaustive and best_parser is not None and getattr(parser, "max_confidence", 1.0) <= best_confidence:
                candidates.append(
                    {
                        "vendor": parser.vendor_name,
                        "parser": parser.__class__.__name__,
                        "version": parser.parser_version,
                        "matched": None,
                        "confidence": None,
                        "info": {},
                        "skipped": f"outscored by {best_parser.vendor_name}",
                    }
                )
                continue

            try:
                matched, confidence, info = parser.detect(evidence_path)
            except Exception as exc:
                matched, confidence, info = False, 0.0, {"error": f"{type(exc).__name__}: {exc}"}

            candidates.append(
                {
                    "vendor": parser.vendor_name,
                    "parser": parser.__class__.__name__,
                    "version": parser.parser_version,
                    "matched": matched,
                    "confidence": confidence,
                    "info": info,
                }
            )

            if matched and confidence > best_confidence:
                best_parser, best_confidence, best_info = parser, confidence, info

        return best_parser, best_confidence, best_info, candidates

    def detect(self, evidence_path: str) -> tuple[BaseDVRParser | None, float, dict]:
        """Try each registered parser's detect(); return the first/best match."""
        parser, confidence, info, _ = self.detect_candidates(evidence_path, exhaustive=False)
        return parser, confidence, info

    def parse(
        self,
        evidence_path: str,
        output_directory: str,
        detection_result: tuple[BaseDVRParser | None, float, dict, list[dict]] | tuple[BaseDVRParser | None, float, dict] | None = None,
    ) -> ParseResult:
        if detection_result is not None:
            if len(detection_result) == 4:
                parser, confidence, info, candidates = detection_result
            else:
                parser, confidence, info = detection_result[:3]
                candidates = [
                    {
                        "vendor": parser.vendor_name,
                        "parser": parser.__class__.__name__,
                        "version": parser.parser_version,
                        "matched": True,
                        "confidence": confidence,
                        "info": info,
                    }
                ] if parser else []
        else:
            parser, confidence, info, candidates = self.detect_candidates(evidence_path)

        detection_info = {
            "selected_parser": parser.vendor_name if parser else None,
            "confidence": confidence,
            "info": info,
            "candidates": candidates,
        }

        if parser is None:
            ext = Path(evidence_path).suffix.lower()
            is_e01_or_split = ext in SPLIT_OR_CONTAINER_EXTS or any(
                evidence_path.lower().endswith(s) for s in (".e01", ".ex01", ".001")
            )

            if is_e01_or_split:
                return ParseResult(
                    vendor="unknown",
                    parser_version="n/a",
                    success=False,
                    error_code=ParseError.UNSUPPORTED_FORMAT,
                    errors=[
                        f"No registered parser matched evidence file '{evidence_path}'. "
                        "Detected E01/split container format, but E01/split image reassembly is not yet implemented."
                    ],
                    warnings=[
                        "E01/split image reassembly is not implemented; parsers operate on raw disk images directly."
                    ],
                    detection_confidence=confidence,
                    detection_info=detection_info,
                )

            return ParseResult(
                vendor="unknown",
                parser_version="n/a",
                success=False,
                error_code=ParseError.UNSUPPORTED_VENDOR,
                errors=["No registered parser matched this evidence file."],
                detection_confidence=confidence,
                detection_info=detection_info,
            )

        is_valid, warnings = parser.validate(evidence_path)
        if not is_valid:
            return ParseResult(
                vendor=parser.vendor_name,
                parser_version=parser.parser_version,
                success=False,
                error_code=ParseError.CORRUPTED_EVIDENCE,
                errors=warnings,
                detection_confidence=confidence,
                detection_info=detection_info,
            )

        result = parser.parse(evidence_path, output_directory)
        result.warnings = warnings + result.warnings
        result.detection_confidence = confidence
        result.detection_info = detection_info
        return result

    def extract(
        self,
        evidence_path: str,
        output_directory: str,
        parse_result: ParseResult,
        detection_result: tuple[BaseDVRParser | None, float, dict, list[dict]] | tuple[BaseDVRParser | None, float, dict] | None = None,
    ) -> ParseResult:
        parser = next((p for p in PARSERS if p.vendor_name == parse_result.vendor), None)
        if parser is None or not hasattr(parser, "extract_recordings"):
            conf = parse_result.detection_confidence
            det_info = parse_result.detection_info
            if detection_result is not None:
                if len(detection_result) == 4:
                    _, conf, _, cands = detection_result
                    det_info = det_info or {"confidence": conf, "candidates": cands}
                else:
                    _, conf, _ = detection_result[:3]
            return ParseResult(
                vendor=parse_result.vendor,
                parser_version=parse_result.parser_version,
                success=False,
                error_code=ParseError.EXTRACTION_FAILED,
                errors=["No extraction support for this vendor/parser."],
                detection_confidence=conf,
                detection_info=det_info,
            )
        extract_res = parser.extract_recordings(
            evidence_path, output_directory, parse_result.recordings, parse_result.raw_master_block
        )
        extract_res.detection_confidence = parse_result.detection_confidence
        extract_res.detection_info = parse_result.detection_info
        return extract_res


parser_manager = ParserManager()
