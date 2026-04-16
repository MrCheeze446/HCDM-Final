from __future__ import annotations

import re
from re import Pattern
from typing import Final

from .parser_common import build_finding
from .parser_types import Finding


PatternList = list[tuple[str, Pattern[str]]]

PYTHON_CRASH_PATTERNS: Final[PatternList] = [
    (
        "exception_traceback",
        re.compile(r"traceback \(most recent call last\):", re.IGNORECASE),
    ),
    (
        "syntax_error",
        re.compile(r"\bsyntaxerror\b", re.IGNORECASE),
    ),
    (
        "import_error",
        re.compile(r"\b(importerror|modulenotfounderror)\b", re.IGNORECASE),
    ),
    (
        "assertion_error",
        re.compile(r"\bassertionerror\b", re.IGNORECASE),
    ),
    (
        "memory_error",
        re.compile(r"\b(memoryerror|fatal python error)\b", re.IGNORECASE),
    ),
]


def detect_python_log(log_text: str) -> bool:
    lowered = log_text.lower()
    return "traceback (most recent call last):" in lowered or "modulenotfounderror" in lowered


def find_python_crash_type(line: str) -> str | None:
    for crash_type, pattern in PYTHON_CRASH_PATTERNS:
        if pattern.search(line):
            return crash_type
    return None


def collect_python_crash(lines: list[str], start_index: int, crash_type: str) -> Finding:
    end_index = start_index
    for cursor in range(start_index + 1, len(lines)):
        candidate = lines[cursor]
        if not candidate.strip():
            break
        end_index = cursor
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*(Error|Exception|Warning)\b", candidate.strip()):
            break

    return build_finding(
        lines=lines,
        start_line=start_index + 1,
        end_line=end_index + 1,
        category="crash",
        finding_type=crash_type,
        message=lines[end_index].strip(),
    )
