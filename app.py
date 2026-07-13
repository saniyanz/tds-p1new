"""Flask entrypoint for the TDS automation agent.

Endpoints (preserved for evaluation compatibility):
- POST /run?task=...      plan + execute a natural-language task
- GET  /read?path=...     read a file under /data
- GET  /filter_csv?...    filter a CSV under /data by column/value
- GET  /healthz           liveness probe
"""
from __future__ import annotations

import csv
import os

from agent import dispatch, plan_task
from core.config import settings
from core.logging import get_logger, log_event
from core.security import PathSecurityError, validate_path
from flask import Flask, Response, jsonify, request

logger = get_logger("api", settings.log_level)

app = Flask(__name__)


@app.route("/run", methods=["POST"])
def run_task():
    task = request.args.get("task")
    if not task:
        return jsonify({"error": "No task provided"}), 400
    try:
        operations, translated = plan_task(task)
        log_event(logger, 20, "task planned", operations=len(operations))
        result = dispatch(operations, translated)
        return jsonify({"result": result}), 200
    except ValueError as ve:
        return jsonify({"error": str(ve)}), 400
    except Exception as e:  # noqa: BLE001
        logger.exception("agent error")
        return jsonify({"error": "Agent error: " + str(e)}), 500


@app.route("/read", methods=["GET"])
def read_file():
    file_path = request.args.get("path")
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    file_path = file_path.strip()
    if file_path.startswith("/data/"):
        file_path = file_path[len("/data/"):]

    try:
        absolute_path = validate_path(file_path, settings.data_dir)
    except PathSecurityError:
        return jsonify({"error": "Access to this file is not allowed"}), 403

    if not absolute_path.exists():
        return "", 404
    try:
        content = absolute_path.read_text(encoding="utf-8")
        return Response(content, mimetype="text/plain"), 200
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": "Error reading file: " + str(e)}), 500


@app.route("/filter_csv", methods=["GET"])
def filter_csv():
    file_path = request.args.get("path")
    filter_column = request.args.get("column")
    filter_value = request.args.get("value")
    if not (file_path and filter_column and filter_value):
        return jsonify({"error": "Missing required parameters."}), 400

    try:
        absolute_path = validate_path(file_path, settings.data_dir)
    except PathSecurityError:
        return jsonify({"error": "Access to this file is not allowed"}), 403
    if not absolute_path.exists():
        return jsonify({"error": "CSV file not found."}), 404

    filtered_rows = []
    with open(absolute_path, encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            if row.get(filter_column) == filter_value:
                filtered_rows.append(row)
    return jsonify(filtered_rows), 200


@app.route("/healthz", methods=["GET"])
def healthz():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    cert = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cert.pem")
    key = os.path.join(os.path.dirname(os.path.abspath(__file__)), "key.pem")
    ssl_context = (cert, key) if (os.path.exists(cert) and os.path.exists(key)) else None
    app.run(debug=False, host=settings.host, port=settings.port, ssl_context=ssl_context)
