from __future__ import annotations

import json
import mimetypes
import os
import re
import secrets
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from kano_core.io import load_survey, save_survey
from kano_core.models import KanoSurvey
from kano_core.service import analyze_kano_payload
from kano_core.validation import KanoValidationError


BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "webui"
SURVEYS_DIR = BASE_DIR / "surveys"
RESPONSES_DIR = BASE_DIR / "responses"
LEGACY_DEFAULT_SURVEY = BASE_DIR / "telega.json"
DEFAULT_SURVEY_ID = "telega"

SURVEYS_DIR.mkdir(exist_ok=True)
RESPONSES_DIR.mkdir(exist_ok=True)


def survey_file_path(survey_id: str) -> Path:
    return SURVEYS_DIR / f"{survey_id}.json"


def response_file_path(survey_id: str) -> Path:
    return RESPONSES_DIR / f"{survey_id}.json"


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-Я]+", "-", title.strip().lower(), flags=re.UNICODE)
    cleaned = cleaned.strip("-")
    return cleaned or "survey"


def generate_survey_id(title: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    token = secrets.token_hex(2)
    return f"{slugify_title(title)}-{stamp}-{token}"


def next_feature_id(index: int) -> str:
    return f"А{index}"


def load_survey_by_id(survey_id: str):
    file_path = survey_file_path(survey_id)
    if file_path.exists():
        return load_survey(file_path)
    if survey_id == DEFAULT_SURVEY_ID and LEGACY_DEFAULT_SURVEY.exists():
        return load_survey(LEGACY_DEFAULT_SURVEY)
    raise FileNotFoundError(f"Опросник '{survey_id}' не найден.")


def read_response_store(survey_id: str) -> list[dict]:
    path = response_file_path(survey_id)
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    return payload if isinstance(payload, list) else []


def write_response_store(survey_id: str, responses: list[dict]) -> None:
    response_file_path(survey_id).write_text(
        json.dumps(responses, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def append_response(survey_id: str, response: dict) -> int:
    responses = read_response_store(survey_id)
    responses.append(response)
    write_response_store(survey_id, responses)
    return len(responses)


def clear_responses(survey_id: str) -> None:
    write_response_store(survey_id, [])


def list_surveys() -> list[dict]:
    items: list[dict] = []

    if LEGACY_DEFAULT_SURVEY.exists():
        survey = load_survey(LEGACY_DEFAULT_SURVEY)
        items.append(build_survey_metadata(DEFAULT_SURVEY_ID, survey))

    for path in sorted(SURVEYS_DIR.glob("*.json")):
        survey_id = path.stem
        if survey_id == DEFAULT_SURVEY_ID and LEGACY_DEFAULT_SURVEY.exists():
            continue
        survey = load_survey(path)
        items.append(build_survey_metadata(survey_id, survey))

    return items


def build_survey_metadata(survey_id: str, survey) -> dict:
    responses = read_response_store(survey_id)
    title = survey.title or f"Опрос {survey_id}"
    return {
        "survey_id": survey_id,
        "title": title,
        "feature_count": len(survey.features),
        "respondent_count": len(responses),
        "survey_url": f"/survey/{survey_id}",
        "dashboard_url": f"/dashboard/{survey_id}",
    }


class KanoWebHandler(BaseHTTPRequestHandler):
    server_version = "KanoWeb/0.3"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/":
            # Serve login page as the site entry point
            self._serve_file(WEB_DIR / "login.html")
            return
        if path in {"/home", "/home.html"}:
            self._serve_file(WEB_DIR / "home.html")
            return
        if path in {"/builder", "/builder.html"}:
            self._serve_file(WEB_DIR / "builder.html")
            return
        if path == "/survey" or path.startswith("/survey/"):
            self._serve_file(WEB_DIR / "survey.html")
            return
        if path == "/dashboard" or path.startswith("/dashboard/"):
            self._serve_file(WEB_DIR / "dashboard.html")
            return
        if path.startswith("/assets/"):
            self._serve_file(WEB_DIR / path.removeprefix("/assets/"))
            return
        if path == "/api/health":
            self._send_json({"status": "ok"})
            return
        if path == "/api/surveys":
            self._send_json({"items": list_surveys()})
            return
        if path == "/api/survey":
            self._handle_get_survey(parsed.query)
            return
        if path == "/api/responses":
            self._handle_get_responses(parsed.query)
            return
        if path.startswith("/generated/"):
            self._serve_file(BASE_DIR / path.removeprefix("/generated/"))
            return

        self._send_json({"error": "Маршрут не найден."}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"

        if path == "/api/surveys":
            self._handle_create_survey()
            return
        if path == "/api/respond":
            self._handle_respond()
            return
        if path == "/api/analyze":
            self._handle_analyze()
            return
        if path == "/api/responses/clear":
            self._handle_clear_responses()
            return
        if path == "/api/survey/delete":
            self._handle_delete_survey()
            return

        self._send_json({"error": "Маршрут не найден."}, status=HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: object) -> None:
        return

    def _handle_get_survey(self, query: str) -> None:
        params = parse_qs(query)
        survey_id = params.get("id", [DEFAULT_SURVEY_ID])[0]
        try:
            survey = load_survey_by_id(survey_id)
        except FileNotFoundError:
            self._send_json({"error": f"Опросник '{survey_id}' не найден."}, status=HTTPStatus.NOT_FOUND)
            return
        except KanoValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(
            {
                "survey_id": survey_id,
                "survey": survey.as_dict(),
                "questionnaire": survey.questionnaire_table(),
                "survey_url": f"/survey/{survey_id}",
                "dashboard_url": f"/dashboard/{survey_id}",
            }
        )

    def _handle_get_responses(self, query: str) -> None:
        params = parse_qs(query)
        survey_id = params.get("id", [DEFAULT_SURVEY_ID])[0]
        responses = read_response_store(survey_id)
        self._send_json(
            {
                "survey_id": survey_id,
                "respondent_count": len(responses),
            }
        )

    def _handle_create_survey(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        title = str(payload.get("title", "")).strip()
        raw_features = payload.get("features", [])
        if not title:
            self._send_json({"error": "Название опроса обязательно."}, status=HTTPStatus.BAD_REQUEST)
            return
        if not isinstance(raw_features, list) or not raw_features:
            self._send_json({"error": "Нужно добавить хотя бы одно свойство."}, status=HTTPStatus.BAD_REQUEST)
            return

        features = []
        for index, feature in enumerate(raw_features, start=1):
            name = str(feature.get("name", "")).strip()
            description = str(feature.get("description", "")).strip()
            if not name:
                self._send_json({"error": f"Свойство #{index} не содержит название."}, status=HTTPStatus.BAD_REQUEST)
                return
            features.append(
                {
                    "feature_id": next_feature_id(index),
                    "name": name,
                    "description": description,
                }
            )

        survey_id = generate_survey_id(title)
        survey_payload = {"title": title, "features": features}

        try:
            survey = KanoSurvey.from_dict(survey_payload)
            save_survey(survey, survey_file_path(survey_id))
            clear_responses(survey_id)
        except KanoValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        self._send_json(
            {
                "status": "created",
                "survey_id": survey_id,
                "title": title,
                "survey_url": f"/survey/{survey_id}",
                "dashboard_url": f"/dashboard/{survey_id}",
            },
            status=HTTPStatus.CREATED,
        )

    def _handle_respond(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        survey_id = str(payload.get("survey_id", DEFAULT_SURVEY_ID)).strip()
        response = payload.get("response")

        if not isinstance(response, dict) or not response:
            self._send_json({"error": "Поле 'response' обязательно и должно содержать ответы респондента."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            load_survey_by_id(survey_id)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        total = append_response(survey_id, response)
        self._send_json(
            {
                "status": "accepted",
                "survey_id": survey_id,
                "respondent_count": total,
            },
            status=HTTPStatus.CREATED,
        )

    def _handle_analyze(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        survey_id = str(payload.get("survey_id", DEFAULT_SURVEY_ID)).strip()
        create_chart = bool(payload.get("create_chart", True))

        try:
            survey = load_survey_by_id(survey_id)
        except FileNotFoundError:
            self._send_json({"error": f"Опросник '{survey_id}' не найден."}, status=HTTPStatus.NOT_FOUND)
            return
        except KanoValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return

        responses = read_response_store(survey_id)
        if not responses:
            self._send_json({"error": "По этому опроснику пока нет ни одного респондента."}, status=HTTPStatus.BAD_REQUEST)
            return

        chart_name = f"kano_matrix_{survey_id}.png"
        try:
            result = analyze_kano_payload(
                survey_payload=survey.as_dict(),
                responses=responses,
                create_chart=create_chart,
                chart_path=chart_name,
            )
        except KanoValidationError as exc:
            self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
            return
        except Exception as exc:
            self._send_json({"error": f"Ошибка анализа: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        chart_path = result.get("summary", {}).get("chart_path")
        if chart_path:
            result["summary"]["chart_url"] = f"/generated/{Path(chart_path).name}"
        result["summary"]["respondent_count"] = len(responses)
        result["survey_id"] = survey_id
        result["survey_url"] = f"/survey/{survey_id}"
        result["dashboard_url"] = f"/dashboard/{survey_id}"
        self._send_json(result)

    def _handle_clear_responses(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        survey_id = str(payload.get("survey_id", DEFAULT_SURVEY_ID)).strip()
        clear_responses(survey_id)
        self._send_json({"status": "cleared", "survey_id": survey_id, "respondent_count": 0})

    def _handle_delete_survey(self) -> None:
        payload = self._read_json_body()
        if payload is None:
            return

        survey_id = str(payload.get("survey_id", "")).strip()
        if not survey_id:
            self._send_json({"error": "Укажите survey_id для удаления."}, status=HTTPStatus.BAD_REQUEST)
            return

        if survey_id == DEFAULT_SURVEY_ID:
            self._send_json(
                {"error": "Базовый опрос telega удалить нельзя."},
                status=HTTPStatus.BAD_REQUEST,
            )
            return

        survey_path = survey_file_path(survey_id)
        if not survey_path.exists():
            self._send_json({"error": f"Опросник '{survey_id}' не найден."}, status=HTTPStatus.NOT_FOUND)
            return

        try:
            os.remove(survey_path)
            response_path = response_file_path(survey_id)
            if response_path.exists():
                os.remove(response_path)
        except OSError as exc:
            self._send_json({"error": f"Не удалось удалить опрос: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json({"status": "deleted", "survey_id": survey_id})

    def _read_json_body(self) -> dict | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        raw_body = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            self._send_json({"error": "Некорректный JSON в запросе."}, status=HTTPStatus.BAD_REQUEST)
            return None
        return payload

    def _serve_file(self, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._send_json({"error": "Файл не найден."}, status=HTTPStatus.NOT_FOUND)
            return

        content_type, _ = mimetypes.guess_type(path.name)
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type or "application/octet-stream")
        self.send_header("Content-Length", str(path.stat().st_size))
        self.end_headers()
        self.wfile.write(path.read_bytes())

    def _send_json(self, payload: dict, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host: str = "127.0.0.1", port: int = 8000) -> None:
    server = ThreadingHTTPServer((host, port), KanoWebHandler)
    print(f"Kano builder: http://{host}:{port}/builder")
    print(f"Kano home: http://{host}:{port}/")
    print(f"Kano respondent UI: http://{host}:{port}/survey/{DEFAULT_SURVEY_ID}")
    print(f"Kano dashboard: http://{host}:{port}/dashboard")
    server.serve_forever()


if __name__ == "__main__":
    run(host="0.0.0.0", port=8000)
