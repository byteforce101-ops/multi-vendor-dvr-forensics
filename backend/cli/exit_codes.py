"""Exit codes returned by the dvrforensics CLI.

Kept centralized so command modules stay consistent and scripts/CI wrapping
the CLI can branch on stable, documented codes instead of parsing text.
"""


class ExitCode:
    OK = 0
    GENERAL_ERROR = 1
    FILE_NOT_FOUND = 2
    UNSUPPORTED_VENDOR = 3
    CORRUPTED_EVIDENCE = 4
    DATABASE_ERROR = 5
    EXTRACTION_FAILED = 6
    MISSING_DEPENDENCY = 7
    INVALID_ARGUMENT = 8
    NOT_FOUND = 9
