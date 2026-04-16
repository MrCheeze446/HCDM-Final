from __future__ import annotations

from .parser_types import Finding, FindingCategory


def build_finding(
    lines: list[str],
    start_line: int,
    end_line: int,
    category: FindingCategory,
    finding_type: str,
    message: str,
) -> Finding:
    context = "\n".join(lines[start_line - 1 : end_line])
    return {
        "line_number": start_line,
        "end_line_number": end_line,
        "category": category,
        "type": finding_type,
        "message": message,
        "context": context,
    }
