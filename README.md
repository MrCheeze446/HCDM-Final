# Log Analyzer

A lightweight web app for parsing log files and surfacing "interesting" events.

Current support:

- Python logs
- C/C++ logs
- AddressSanitizer crash reports
- Warning detection
- Crash detection with basic crash subtype classification
- Multi-line crash grouping for tracebacks and related failure blocks

## Run locally

```bash
uv run python app.py
```

Then open `http://127.0.0.1:8000`.

## Setup

```bash
uv sync
```

This creates the local `.venv` and installs project tooling, including `basedpyright`.

## Type checking

```bash
uv run basedpyright app.py log_parser.py test_log_parser.py
```

## What it detects today

- Warnings such as `warning`, `deprecated`, and Python warning classes
- Python crashes such as tracebacks, syntax errors, import errors, assertion errors, and memory errors
- C/C++ crashes such as segmentation faults, assertion failures, aborts, floating point exceptions, stack smashing, and undefined references
- AddressSanitizer reports such as `SEGV`, `heap-use-after-free`, `heap-buffer-overflow`, and related memory safety failures

## Notes

- Language can be selected manually or auto-detected from the log text.
- This is intentionally rules-based for now so it is easy to extend with more patterns later.
- Crash findings include `line_number` and `end_line_number` so the frontend can show the full block that was matched.
