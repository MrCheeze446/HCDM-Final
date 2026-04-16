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
or
```bash
python app.py
```

Then open `http://127.0.0.1:8000`.

## Setup

This project uses uv for any dependecies. Although not strictly required it helps with thing like type checking. To use uv with the project run ``uv sync``

## What it detects currently

- Warnings such as `warning`, `deprecated`, and Python warning classes
- Python crashes such as tracebacks, syntax errors, import errors, assertion errors, and memory errors
- C/C++ crashes such as segmentation faults, assertion failures, aborts, floating point exceptions, stack smashing, and undefined references
- AddressSanitizer reports such as `SEGV`, `heap-use-after-free`, `heap-buffer-overflow`, and related memory safety failures
