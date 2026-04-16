from __future__ import annotations

from typing import Literal, TypedDict


Language = Literal["python", "c_cpp", "generic"]
FindingCategory = Literal["warning", "crash"]


class Finding(TypedDict):
    line_number: int
    end_line_number: int
    category: FindingCategory
    type: str
    message: str
    context: str


class Summary(TypedDict):
    total_findings: int
    warnings: int
    crashes: int


class AnalysisResult(TypedDict):
    language: Language
    summary: Summary
    crash_types: dict[str, int]
    findings: list[Finding]
