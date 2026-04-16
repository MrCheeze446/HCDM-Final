from __future__ import annotations

import re
from re import Pattern
from typing import Final

from .parser_common import build_finding
from .parser_types import Finding


PatternList = list[tuple[str, Pattern[str]]]

C_CRASH_PATTERNS: Final[PatternList] = [
    (
        "asan_segv",
        re.compile(r"addresssanitizer:\s*segv", re.IGNORECASE),
    ),
    (
        "asan_heap_use_after_free",
        re.compile(r"addresssanitizer:\s*heap-use-after-free", re.IGNORECASE),
    ),
    (
        "asan_stack_buffer_overflow",
        re.compile(r"addresssanitizer:\s*stack-buffer-overflow", re.IGNORECASE),
    ),
    (
        "asan_heap_buffer_overflow",
        re.compile(r"addresssanitizer:\s*heap-buffer-overflow", re.IGNORECASE),
    ),
    (
        "asan_global_buffer_overflow",
        re.compile(r"addresssanitizer:\s*global-buffer-overflow", re.IGNORECASE),
    ),
    (
        "asan_use_after_poison",
        re.compile(r"addresssanitizer:\s*use-after-poison", re.IGNORECASE),
    ),
    (
        "asan_double_free",
        re.compile(r"addresssanitizer:\s*attempting double-free", re.IGNORECASE),
    ),
    (
        "asan_bad_free",
        re.compile(r"addresssanitizer:\s*attempting free on address which was not malloc", re.IGNORECASE),
    ),
    (
        "asan_deadly_signal",
        re.compile(r"addresssanitizer:\s*deadlysignal", re.IGNORECASE),
    ),
    (
        "segmentation_fault",
        re.compile(r"\b(segmentation fault|sigsegv)\b", re.IGNORECASE),
    ),
    (
        "assertion_failure",
        re.compile(r"\b(assertion .* failed|assert failed)\b", re.IGNORECASE),
    ),
    (
        "abort_signal",
        re.compile(r"\b(aborted|sigabrt)\b", re.IGNORECASE),
    ),
    (
        "floating_point_exception",
        re.compile(r"\b(floating point exception|sigfpe)\b", re.IGNORECASE),
    ),
    (
        "stack_smashing",
        re.compile(r"\bstack smashing detected\b", re.IGNORECASE),
    ),
    (
        "undefined_reference",
        re.compile(r"\bundefined reference to\b", re.IGNORECASE),
    ),
]


def detect_c_cpp_log(log_text: str) -> bool:
    lowered = log_text.lower()
    return (
        "segmentation fault" in lowered
        or "undefined reference to" in lowered
        or "addresssanitizer:" in lowered
    )


def find_c_cpp_crash_type(line: str) -> str | None:
    for crash_type, pattern in C_CRASH_PATTERNS:
        if pattern.search(line):
            return crash_type
    return None


def collect_c_cpp_crash(lines: list[str], start_index: int, crash_type: str) -> Finding:
    if crash_type.startswith("asan_"):
        return collect_asan_crash(lines, start_index, crash_type)

    end_index = start_index
    for cursor in range(start_index + 1, len(lines)):
        candidate = lines[cursor].strip()
        if not candidate:
            break
        if looks_like_c_cpp_continuation(candidate):
            end_index = cursor
            continue
        break

    return build_finding(
        lines=lines,
        start_line=start_index + 1,
        end_line=end_index + 1,
        category="crash",
        finding_type=crash_type,
        message=lines[start_index].strip(),
    )


def collect_asan_crash(lines: list[str], start_index: int, crash_type: str) -> Finding:
    end_index = start_index
    summary_line = lines[start_index].strip()
    resolved_crash_type = crash_type
    trailing_blank_lines = 0

    for cursor in range(start_index + 1, len(lines)):
        candidate = lines[cursor].strip()
        if not candidate:
            trailing_blank_lines += 1
            end_index = cursor
            if trailing_blank_lines > 2:
                break
            continue

        trailing_blank_lines = 0
        end_index = cursor
        if "ERROR: AddressSanitizer:" in candidate:
            resolved_crash_type = classify_asan_line(candidate)
            if summary_line == lines[start_index].strip():
                summary_line = candidate
            continue
        if candidate.startswith("SUMMARY: AddressSanitizer:"):
            summary_line = candidate
            resolved_crash_type = classify_asan_line(candidate)
            continue
        if candidate.endswith("ABORTING") or candidate == "AddressSanitizer can not provide additional info.":
            continue
        if cursor > start_index and is_new_asan_header(candidate, resolved_crash_type):
            end_index = cursor - 1
            break

    return build_finding(
        lines=lines,
        start_line=start_index + 1,
        end_line=end_index + 1,
        category="crash",
        finding_type=resolved_crash_type,
        message=summary_line,
    )


def classify_asan_line(line: str) -> str:
    for crash_type, pattern in C_CRASH_PATTERNS:
        if crash_type.startswith("asan_") and pattern.search(line):
            return crash_type
    return "asan_deadly_signal"


def is_new_asan_header(line: str, current_crash_type: str) -> bool:
    if line.startswith("==") and "ERROR: AddressSanitizer:" in line:
        return current_crash_type != classify_asan_line(line)
    return False


def looks_like_c_cpp_continuation(line: str) -> bool:
    if line.startswith(
        (
            "^",
            "at ",
            "#",
            "note:",
            "collect2:",
            "ld:",
            "clang:",
            "gcc:",
            "SUMMARY:",
            "AddressSanitizer",
            "==",
        )
    ):
        return True
    return (
        "core dumped" in line.lower()
        or "detected" in line.lower()
        or "referenced from" in line.lower()
        or line.startswith(("/", "./"))
    )
