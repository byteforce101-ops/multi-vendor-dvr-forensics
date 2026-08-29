"""
ParserManager: detects which vendor parser applies to a given evidence file
and dispatches to it. New vendors register themselves in PARSERS below —
nothing else in the app should need to change to add one.
"""

from backend.parsers.common.base import BaseDVRParser, ParseResult, ParseError
from backend.parsers.hikvision.parser import HikvisionParser
from backend.parsers.heimvision.parser import HeimVisionParser
from backend.parsers.generic.parser import GenericVideoParser
# Order matters: more specific/proprietary parsers should be tried before
# the generic fallback. Dahua's parser slots in here once it exists.
PARSERS: list[BaseDVRParser] = [
    HikvisionParser(),
    HeimVisionParser(),
    GenericVideoParser(),
]


class ParserManager:
    def detect(self, evidence_path: str) -> tuple[BaseDVRParser | None, float, dict]:
        """Try each registered parser's detect(); return the first/best match."""
        best_parser, best_confidence, best_info = None, 0.0, {}
        for parser in PARSERS:
            try:
                matched, confidence, info = parser.detect(evidence_path)
            except Exception:
                continue  # a parser's detect() must never take down the whole detection pass
            if matched and confidence > best_confidence:
                best_parser, best_confidence, best_info = parser, confidence, info
        return best_parser, best_confidence, best_info

    def parse(self, evidence_path: str, output_directory: str) -> ParseResult:
        parser, confidence, info = self.detect(evidence_path)
        if parser is None:
            return ParseResult(
                vendor="unknown",
                parser_version="n/a",
                success=False,
                error_code=ParseError.UNSUPPORTED_VENDOR,
                errors=["No registered parser matched this evidence file."],
            )

        is_valid, warnings = parser.validate(evidence_path)
        if not is_valid:
            return ParseResult(
                vendor=parser.vendor_name,
                parser_version=parser.parser_version,
                success=False,
                error_code=ParseError.CORRUPTED_EVIDENCE,
                errors=warnings,
            )

        result = parser.parse(evidence_path, output_directory)
        result.warnings = warnings + result.warnings
        return result

    def extract(
        self, evidence_path: str, output_directory: str, parse_result: ParseResult
    ) -> ParseResult:
        parser = next((p for p in PARSERS if p.vendor_name == parse_result.vendor), None)
        if parser is None or not hasattr(parser, "extract_recordings"):
            return ParseResult(
                vendor=parse_result.vendor,
                parser_version=parse_result.parser_version,
                success=False,
                error_code=ParseError.EXTRACTION_FAILED,
                errors=["No extraction support for this vendor/parser."],
            )
        return parser.extract_recordings(
            evidence_path, output_directory, parse_result.recordings, parse_result.raw_master_block
        )
