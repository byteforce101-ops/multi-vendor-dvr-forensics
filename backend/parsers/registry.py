"""
ParserManager: detects which vendor parser applies to a given evidence file
and dispatches to it. New vendors register themselves in PARSERS below —
nothing else in the app should need to change to add one.
"""

import logging
from pathlib import Path
from backend.parsers.common.base import BaseDVRParser, ParseResult, ParseError
from backend.parsers.hikvision.parser import HikvisionParser
from backend.parsers.dahua.parser import DahuaParser
from backend.parsers.tplink.parser import TPLinkVigiParser
from backend.parsers.heimvision.parser import HeimVisionParser
from backend.parsers.uniview.parser import UnivewParser
from backend.parsers.cpplus.parser import CPPlusParser
from backend.parsers.carver.parser import ForensicDiskCarverParser
from backend.parsers.generic.parser import GenericVideoParser

logger = logging.getLogger(__name__)

# Order matters: more specific/proprietary parsers should be tried before
# disk carvers and generic fallbacks. The max_confidence of each parser
# controls short-circuit skipping once a high-confidence match is found.
#
#   HikvisionParser   max_confidence=0.90  — HIKVISION@HANGZHOU signature
#   DahuaParser        max_confidence=0.90  — DHFS4.1 signature / DHAV frames
#   TPLinkVigiParser   max_confidence=0.80  — DHAV + TP-Link brand strings
#   HeimVisionParser   max_confidence=0.75  — HEVC VPS markers
#   UnivewParser       max_confidence=0.75  — Uniview brand strings + NAL carving
#   CPPlusParser       max_confidence=0.72  — Dahua OEM + CP Plus brand strings
#   ForensicDiskCarver max_confidence=0.65  — generic MPEG-PS carver
#   GenericVideoParser max_confidence=0.30  — last resort
PARSERS: list[BaseDVRParser] = [
    HikvisionParser(),
    DahuaParser(),
    TPLinkVigiParser(),
    HeimVisionParser(),
    UnivewParser(),
    CPPlusParser(),
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

        p = Path(evidence_path)
        file_size = p.stat().st_size if p.exists() else None
        mtime_ns = p.stat().st_mtime_ns if p.exists() else None
        norm_path = str(p.resolve()) if p.exists() else str(evidence_path)

        if best_info is not None and isinstance(best_info, dict):
            best_info["evidence_path"] = norm_path
            best_info["file_size"] = file_size
            best_info["mtime_ns"] = mtime_ns

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
        p = Path(evidence_path)
        curr_size = p.stat().st_size if p.exists() else None
        curr_mtime = p.stat().st_mtime_ns if p.exists() else None
        curr_norm = str(p.resolve()) if p.exists() else str(evidence_path)

        if detection_result is not None:
            cand_info = None
            if len(detection_result) >= 3 and isinstance(detection_result[2], dict):
                cand_info = detection_result[2]

            mismatch = False
            if cand_info:
                det_path = cand_info.get("evidence_path")
                det_size = cand_info.get("file_size")
                det_mtime = cand_info.get("mtime_ns")

                if det_path is not None and (det_path != curr_norm and det_path != str(evidence_path)):
                    mismatch = True
                elif det_size is not None and det_size != curr_size:
                    mismatch = True
                elif det_mtime is not None and det_mtime != curr_mtime:
                    mismatch = True

            if mismatch:
                logger.warning(
                    f"Precomputed detection result does not match evidence file '{evidence_path}'. "
                    "Ignoring precomputed detection result and re-detecting."
                )
                detection_result = None

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
            "evidence_path": curr_norm,
            "file_size": curr_size,
            "mtime_ns": curr_mtime,
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
        p = Path(evidence_path)
        curr_size = p.stat().st_size if p.exists() else None
        curr_mtime = p.stat().st_mtime_ns if p.exists() else None
        curr_norm = str(p.resolve()) if p.exists() else str(evidence_path)

        if detection_result is not None:
            cand_info = None
            if len(detection_result) >= 3 and isinstance(detection_result[2], dict):
                cand_info = detection_result[2]

            mismatch = False
            if cand_info:
                det_path = cand_info.get("evidence_path")
                det_size = cand_info.get("file_size")
                det_mtime = cand_info.get("mtime_ns")

                if det_path is not None and (det_path != curr_norm and det_path != str(evidence_path)):
                    mismatch = True
                elif det_size is not None and det_size != curr_size:
                    mismatch = True
                elif det_mtime is not None and det_mtime != curr_mtime:
                    mismatch = True

            if mismatch:
                logger.warning(
                    f"Precomputed detection result does not match evidence file '{evidence_path}'. "
                    "Ignoring precomputed detection result."
                )
                detection_result = None

        parser = next((p for p in PARSERS if p.vendor_name == parse_result.vendor), None)
        if parser is None or not hasattr(parser, "extract_recordings"):
            conf = parse_result.detection_confidence
            det_info = parse_result.detection_info
            if detection_result is not None:
                if len(detection_result) == 4:
                    _, conf, _, cands = detection_result
                    det_info = det_info or {
                        "evidence_path": curr_norm,
                        "file_size": curr_size,
                        "mtime_ns": curr_mtime,
                        "confidence": conf,
                        "candidates": cands,
                    }
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
