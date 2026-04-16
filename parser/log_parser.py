from __future__ import annotations

import re
from collections import Counter
from re import Pattern
from typing import Final

from .c_cpp_log_parser import collect_c_cpp_crash, detect_c_cpp_log, find_c_cpp_crash_type
from .parser_common import build_finding
from .parser_types import AnalysisResult, Finding, Language
from .python_log_parser import collect_python_crash, detect_python_log, find_python_crash_type


WARNING_PATTERNS: Final[list[Pattern[str]]] = [
    re.compile(r"\bwarning\b", re.IGNORECASE),
    re.compile(r"\bdeprecated\b", re.IGNORECASE),
    re.compile(r"\bresourcewarning\b", re.IGNORECASE),
    re.compile(r"\bruntimewarning\b", re.IGNORECASE),
    re.compile(r"\bsyntaxwarning\b", re.IGNORECASE),
    re.compile(r"\buserwarning\b", re.IGNORECASE),
]

GENERIC_CRASH_PATTERNS: Final[list[tuple[str, Pattern[str]]]] = [
    (
        "timeout",
        re.compile(r"\b(timeout|timed out)\b", re.IGNORECASE),
    ),
    (
        "fatal_error",
        re.compile(r"\bfatal\b", re.IGNORECASE),
    ),
    (
        "panic_or_terminate",
        re.compile(r"\b(terminate called after throwing|panic)\b", re.IGNORECASE),
    ),
]


def analyze_log(log_text: str, language: str = "auto") -> AnalysisResult:
    lines = log_text.splitlines()
    normalized_language = normalize_language(language, log_text)
    findings = collect_warning_findings(lines)
    findings.extend(collect_crash_findings(lines, normalized_language))
    findings.sort(key=lambda finding: finding["line_number"])

    summary = Counter(finding["category"] for finding in findings)
    crash_types = Counter(
        finding["type"] for finding in findings if finding["category"] == "crash"
    )

    return {
        "language": normalized_language,
        "summary": {
            "total_findings": len(findings),
            "warnings": summary.get("warning", 0),
            "crashes": summary.get("crash", 0),
        },
        "crash_types": dict(crash_types),
        "findings": findings,
    }


def normalize_language(language: str, log_text: str) -> Language:
    lowered = language.lower()
    if lowered in {"python", "py"}:
        return "python"
    if lowered in {"c", "c++", "cpp", "cc"}:
        return "c_cpp"
    return detect_language(log_text)


def detect_language(log_text: str) -> Language:
    if detect_python_log(log_text):
        return "python"
    if detect_c_cpp_log(log_text):
        return "c_cpp"
    return "generic"


def find_warning_match(line: str) -> str | None:
    for pattern in WARNING_PATTERNS:
        if pattern.search(line):
            return "warning"
    return None


def find_crash_type(line: str, language: Language) -> str | None:
    if language == "python":
        crash_type = find_python_crash_type(line)
        if crash_type is not None:
            return crash_type
    elif language == "c_cpp":
        crash_type = find_c_cpp_crash_type(line)
        if crash_type is not None:
            return crash_type
    else:
        crash_type = find_python_crash_type(line) or find_c_cpp_crash_type(line)
        if crash_type is not None:
            return crash_type

    for crash_type, pattern in GENERIC_CRASH_PATTERNS:
        if pattern.search(line):
            return crash_type
    return None


def collect_warning_findings(lines: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for index, line in enumerate(lines):
        stripped_line = line.strip()
        if not stripped_line:
            continue

        warning_match = find_warning_match(stripped_line)
        if warning_match is None:
            continue

        findings.append(
            build_finding(
                lines=lines,
                start_line=index + 1,
                end_line=index + 1,
                category="warning",
                finding_type=warning_match,
                message=stripped_line,
            )
        )
    return findings


def collect_crash_findings(lines: list[str], language: Language) -> list[Finding]:
    findings: list[Finding] = []
    consumed_lines: set[int] = set()

    for index, line in enumerate(lines):
        if index in consumed_lines:
            continue

        stripped_line = line.strip()
        if not stripped_line:
            continue

        crash_type = find_crash_type(stripped_line, language)
        if crash_type is None:
            continue

        if language == "python":
            finding = collect_python_crash(lines, index, crash_type)
        elif language == "c_cpp":
            finding = collect_c_cpp_crash(lines, index, crash_type)
        else:
            finding = build_finding(
                lines=lines,
                start_line=index + 1,
                end_line=index + 1,
                category="crash",
                finding_type=crash_type,
                message=stripped_line,
            )

        consumed_lines.update(range(finding["line_number"] - 1, finding["end_line_number"]))
        findings.append(finding)

    return findings
