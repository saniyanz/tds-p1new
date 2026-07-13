"""Flask entrypoint for the TDS automation agent.

Endpoints (preserved for evaluation compatibility):
- POST /run?task=...      plan + execute a natural-language task
- GET  /read?path=...     read a file under /data
- GET  /filter_csv?...    filter a CSV under /data by column/value
- GET  /                  public landing/status page
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

# Optional shared-secret auth. If AGENT_TOKEN is set in the environment, every
# /run, /read and /filter_csv request must include ?token=... or an
# "Authorization: Bearer ..." header. Leave it unset for open (eval) access.
AGENT_TOKEN = os.getenv("AGENT_TOKEN")

_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>TDS Automation Agent</title>
<style>
:root{--bg:#0f172a;--card:#1e293b;--fg:#e2e8f0;--muted:#94a3b8;--accent:#38bdf8;--ok:#34d399;--err:#f87171}
*{box-sizing:border-box}
body{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;background:var(--bg);color:var(--fg);line-height:1.5}
.wrap{max-width:840px;margin:0 auto;padding:2rem 1.2rem 4rem}
h1{margin:0 0 .25rem;font-size:1.6rem}
h3{margin-top:0}
.muted{color:var(--muted)}
.badge{display:inline-block;background:rgba(52,211,153,.15);color:var(--ok);padding:.15rem .6rem;border-radius:999px;font-size:.78rem;margin-left:.5rem;vertical-align:middle}
.card{background:var(--card);border:1px solid #334155;border-radius:12px;padding:1.2rem;margin-top:1.4rem}
label{display:block;font-size:.85rem;color:var(--muted);margin:.8rem 0 .3rem}
textarea,input[type=text]{width:100%;background:#0b1220;border:1px solid #334155;color:var(--fg);border-radius:8px;padding:.7rem;font-size:.95rem;font-family:inherit}
textarea{min-height:92px;resize:vertical}
.row{display:flex;gap:.6rem;flex-wrap:wrap;align-items:center}
button{background:var(--accent);color:#06283d;border:0;border-radius:8px;padding:.7rem 1.2rem;font-weight:600;cursor:pointer;font-size:.95rem}
button:disabled{opacity:.5;cursor:not-allowed}
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin-top:.8rem}
.chip{background:#0b1220;border:1px solid #334155;color:var(--fg);border-radius:999px;padding:.35rem .8rem;font-size:.82rem;cursor:pointer}
.chip:hover{border-color:var(--accent)}
pre{background:#0b1220;border:1px solid #334155;border-radius:8px;padding:.9rem;overflow:auto;white-space:pre-wrap;word-break:break-word;font-size:.9rem;margin-top:1rem;display:none}
input.tok{width:260px}
.status{margin-top:.8rem;font-size:.85rem}
.ok{color:var(--ok)}.err{color:var(--err)}
.endpoint{font-family:ui-monospace,Menlo,monospace;color:var(--accent);font-size:.85rem;margin:.2rem 0}
code{background:#0b1220;padding:.1rem .35rem;border-radius:4px}
ul{line-height:1.9;padding-left:1.1rem}
</style>
</head>
<body>
<div class="wrap">
  <h1>TDS Automation Agent <span class="badge" id="status">checking…</span></h1>
  <p class="muted">Describe a task in plain English. The agent plans it with an LLM and runs the operations on <code>/data</code>.</p>

  <div class="card">
    <label for="task">Your task</label>
    <textarea id="task" placeholder="e.g. Count how many Wednesdays are in /data/dates.txt"></textarea>
    <div class="row" style="margin-top:.9rem">
      <button id="run">Run task</button>
      <input type="text" id="token" class="tok" placeholder="access token (optional)">
    </div>
    <div class="chips" id="examples"></div>
    <div class="status" id="statusLine"></div>
    <pre id="result"></pre>
  </div>

  <div class="card">
    <h3>Supported operations</h3>
    <p class="muted">Click any example chip above to load it. Full operation list:</p>
    <ul id="ops" class="muted"></ul>
  </div>

  <div class="card">
    <h3>API</h3>
    <p class="muted">Same behaviour, programmatic access:</p>
    <p class="endpoint">POST /run?task=&lt;task&gt;</p>
    <p class="endpoint">GET&nbsp; /read?path=&lt;path&gt;</p>
    <p class="endpoint">GET&nbsp; /filter_csv?path=&amp;column=&amp;value=</p>
    <p class="endpoint">GET&nbsp; /healthz</p>
  </div>
</div>

<script>
const EXAMPLES = [
  "Count how many Wednesdays are in /data/dates.txt",
  "Sort the contacts in /data/contacts.json by last name and save to /data/contacts-sorted.json",
  "Write the first line of the 10 most recent .log files in /data/logs to /data/logs-recent.txt",
  "Index the Markdown files in /data/docs and save the index to /data/docs/index.json",
  "Extract the sender's email address from /data/email.txt",
  "Extract the credit card number from /data/credit_card.png",
  "Find the most similar pair of comments in /data/comments.txt",
  "Calculate the total sales of Gold tickets",
  "Format /data/format.md with Prettier"
];
const OPS = [
  "format_file — format format.md with Prettier",
  "count_dates — count dates on a given weekday",
  "sort_contacts — sort contacts.json by name",
  "extract_logs — first lines of 10 newest logs",
  "index_docs — index Markdown docs by H1",
  "extract_email — sender email from email.txt",
  "extract_credit_card — OCR card number from image",
  "find_similar_comments — most similar comment pair",
  "query_tickets — total sales for a ticket type",
  "fetch_api — fetch a URL and save it",
  "clone_git — clone a repo",
  "run_sql_query — run SQL on a DB file",
  "scrape_website — scrape a page to text",
  "resize_image — compress/resize an image",
  "transcribe_audio — transcribe audio to text",
  "md_to_html — convert Markdown to HTML"
];

const taskEl = document.getElementById("task");
const resultEl = document.getElementById("result");
const statusLine = document.getElementById("statusLine");

EXAMPLES.forEach(function (ex) {
  const c = document.createElement("span");
  c.className = "chip";
  c.textContent = ex.length > 44 ? ex.slice(0, 44) + "…" : ex;
  c.title = ex;
  c.onclick = function () { taskEl.value = ex; };
  document.getElementById("examples").appendChild(c);
});
OPS.forEach(function (op) {
  const li = document.createElement("li");
  li.textContent = op;
  document.getElementById("ops").appendChild(li);
});

function checkHealth() {
  fetch("/healthz").then(function (r) { return r.json(); }).then(function (j) {
    const s = document.getElementById("status");
    s.textContent = j.status === "ok" ? "online" : "degraded";
    s.style.color = j.status === "ok" ? "var(--ok)" : "var(--err)";
  }).catch(function () {
    const s = document.getElementById("status");
    s.textContent = "offline"; s.style.color = "var(--err)";
  });
}
checkHealth();

document.getElementById("run").onclick = function () {
  const task = taskEl.value.trim();
  if (!task) { statusLine.innerHTML = '<span class="err">Enter a task first.</span>'; return; }
  const btn = document.getElementById("run");
  btn.disabled = true;
  statusLine.innerHTML = '<span class="muted">Planning &amp; running…</span>';
  resultEl.style.display = "none";
  const tok = document.getElementById("token").value.trim();
  const url = "/run?task=" + encodeURIComponent(task) + (tok ? ("&token=" + encodeURIComponent(tok)) : "");
  fetch(url, { method: "POST" })
    .then(function (res) {
      return res.json().then(function (data) {
        resultEl.style.display = "block";
        resultEl.textContent = JSON.stringify(data, null, 2);
        if (data.result !== undefined) statusLine.innerHTML = '<span class="ok">Done (HTTP ' + res.status + ')</span>';
        else statusLine.innerHTML = '<span class="err">Error (HTTP ' + res.status + ')</span>';
      });
    })
    .catch(function (e) {
      resultEl.style.display = "block";
      resultEl.textContent = String(e);
      statusLine.innerHTML = '<span class="err">Request failed</span>';
    })
    .finally(function () { btn.disabled = false; });
};
</script>
</body></html>"""


@app.route("/", methods=["GET"])
def index():
    return Response(_HTML, mimetype="text/html"), 200


@app.before_request
def _require_token():
    if not AGENT_TOKEN:
        return None
    if request.path in ("/", "/healthz"):
        return None
    provided = request.args.get("token")
    auth = request.headers.get("Authorization", "")
    if not provided and auth.startswith("Bearer "):
        provided = auth[7:]
    if provided != AGENT_TOKEN:
        return jsonify({"error": "unauthorized"}), 401


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
    use_tls = settings.tls_enabled and os.path.exists(cert) and os.path.exists(key)
    ssl_context = (cert, key) if use_tls else None
    app.run(debug=False, host=settings.host, port=settings.port, ssl_context=ssl_context)
