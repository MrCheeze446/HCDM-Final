from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
from typing import TypedDict, cast, override
from urllib.parse import parse_qs, unquote, urlparse

from parser import AnalysisResult, analyze_log


ROOT_DIR = Path(__file__).parent
STATIC_DIR = ROOT_DIR / "static"
EXAMPLE_LOGS_DIR = ROOT_DIR / "example_logs"


class RepoLogSummary(TypedDict):
    name: str
    language: str
    summary: dict[str, int]
    primary_message: str


class RepoLogDetail(TypedDict):
    name: str
    content: str
    analysis: AnalysisResult


class LogAnalyzerHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/logs":
            query_params = parse_qs(parsed.query)
            query = query_params.get("query", [""])[0]
            use_regex = query_params.get("regex", ["0"])[0] == "1"

            try:
                logs = self._build_log_summaries(query=query, use_regex=use_regex)
            except re.error as error:
                self._send_json({"error": f"Invalid regex: {error.msg}"}, HTTPStatus.BAD_REQUEST)
                return

            self._send_json({"logs": logs})
            return

        if path.startswith("/api/logs/"):
            log_name = unquote(path.removeprefix("/api/logs/"))
            log_detail = self._build_log_detail(log_name)
            if log_detail is None:
                self._send_json({"error": "Log not found."}, HTTPStatus.NOT_FOUND)
                return
            self._send_json(log_detail)
            return

        if path == "/" or path == "/index.html":
            self._serve_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        if path == "/styles.css":
            self._serve_file(STATIC_DIR / "styles.css", "text/css; charset=utf-8")
            return

        if path == "/app.js":
            self._serve_file(STATIC_DIR / "app.js", "application/javascript; charset=utf-8")
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Not Found")

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/api/analyze":
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)

        try:
            decoded_body = raw_body.decode("utf-8")
            payload = json.loads(decoded_body)
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._send_json({"error": "Request body must be valid JSON."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(payload, dict):
            self._send_json({"error": "Request body must be a JSON object."}, HTTPStatus.BAD_REQUEST)
            return

        log_text = payload.get("log_text", "")
        language = payload.get("language", "auto")

        if not isinstance(log_text, str) or not log_text.strip():
            self._send_json({"error": "Please provide a non-empty log."}, HTTPStatus.BAD_REQUEST)
            return

        if not isinstance(language, str):
            self._send_json({"error": "Language must be a string."}, HTTPStatus.BAD_REQUEST)
            return

        analysis: AnalysisResult = analyze_log(log_text=log_text, language=language)
        self._send_json(analysis)

    @override
    def log_message(self, format: str, *args: object) -> None:
        return

    def _serve_file(self, file_path: Path, content_type: str) -> None:
        if not file_path.exists():
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
            return

        content = file_path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _send_json(
        self, payload: object, status: HTTPStatus = HTTPStatus.OK
    ) -> None:
        content = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def _build_log_summaries(self, query: str = "", use_regex: bool = False) -> list[RepoLogSummary]:
        summaries: list[RepoLogSummary] = []
        compiled_query = compile_search_pattern(query, use_regex)

        for log_path in sorted(EXAMPLE_LOGS_DIR.iterdir()):
            if not log_path.is_file():
                continue
            log_text = log_path.read_text(encoding="utf-8")
            if not log_matches_query(log_path.name, log_text, compiled_query):
                continue
            analysis = analyze_log(log_text)
            primary_message = analysis["findings"][0]["message"] if analysis["findings"] else "No findings"
            summaries.append(
                {
                    "name": log_path.name,
                    "language": analysis["language"],
                    "summary": cast(dict[str, int], analysis["summary"]),
                    "primary_message": primary_message,
                }
            )
        return summaries

    def _build_log_detail(self, log_name: str) -> RepoLogDetail | None:
        log_path = self._resolve_log_path(log_name)
        if log_path is None or not log_path.exists():
            return None

        log_text = log_path.read_text(encoding="utf-8")
        return {
            "name": log_path.name,
            "content": log_text,
            "analysis": analyze_log(log_text),
        }

    def _resolve_log_path(self, log_name: str) -> Path | None:
        candidate = (EXAMPLE_LOGS_DIR / log_name).resolve()
        logs_root = EXAMPLE_LOGS_DIR.resolve()
        if candidate.parent != logs_root:
            return None
        return candidate


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), LogAnalyzerHandler)
    print(f"Serving log analyzer at http://{host}:{port}")
    server.serve_forever()


def compile_search_pattern(query: str, use_regex: bool) -> re.Pattern[str] | None:
    stripped_query = query.strip()
    if not stripped_query:
        return None
    if use_regex:
        return re.compile(stripped_query, re.IGNORECASE)
    return re.compile(re.escape(stripped_query), re.IGNORECASE)


def log_matches_query(log_name: str, log_text: str, pattern: re.Pattern[str] | None) -> bool:
    if pattern is None:
        return True
    return pattern.search(log_name) is not None or pattern.search(log_text) is not None


if __name__ == "__main__":
    run()
