"""
app.py
------
Flask application entry point for the Policy Conflict & Staleness Detector.

Routes:
    GET  /                  -> upload page
    POST /upload             -> handle file upload form submission, redirect to dashboard
    GET  /dashboard          -> analysis dashboard (renders current in-memory analysis)
    GET  /report             -> HTML report preview page
    GET  /report/pdf         -> download the PDF version of the report
    POST /load-sample        -> load bundled sample_data/*.txt for demo purposes

    REST API:
    POST /api/upload          -> upload files (multipart/form-data), returns parsed doc summary
    GET  /api/analyze         -> run full analysis on currently loaded documents, returns JSON
    GET  /api/report          -> generate + return the PDF report (application/pdf)
"""

import os
from typing import Dict

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    jsonify,
    send_file,
    flash,
)

from analysis import run_analysis, get_internal_objects
from report.report_generator import generate_pdf_report

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DATA_DIR = os.path.join(BASE_DIR, "sample_data")
ALLOWED_EXTENSIONS = {".txt"}

app = Flask(__name__)
app.secret_key = "policy-conflict-detector-hackathon-secret-key"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB upload cap

# In-memory store for the currently loaded raw policy files: {filename: text}.
# This is intentionally simple (single-tenant, in-process) which is
# appropriate for a hackathon demo / single-analyst tool. A production
# deployment would persist this per-user-session or in a database instead.
STATE: Dict[str, str] = {}


def _allowed_file(filename: str) -> bool:
    return os.path.splitext(filename.lower())[1] in ALLOWED_EXTENSIONS


def _load_sample_data() -> None:
    """Populate STATE with the bundled sample_data/*.txt files."""
    STATE.clear()
    for fname in sorted(os.listdir(SAMPLE_DATA_DIR)):
        if not _allowed_file(fname):
            continue
        path = os.path.join(SAMPLE_DATA_DIR, fname)
        with open(path, "r", encoding="utf-8") as f:
            STATE[fname] = f.read()


@app.route("/", methods=["GET"])
def index():
    """Render the upload / landing page."""
    return render_template("index.html", loaded_files=sorted(STATE.keys()))


@app.route("/upload", methods=["POST"])
def upload():
    """Handle the multi-file upload form from the index page."""
    files = request.files.getlist("policy_files")

    if not files or all(f.filename == "" for f in files):
        flash("Please choose at least one .txt policy file to upload.", "warning")
        return redirect(url_for("index"))

    added = 0
    for f in files:
        if f and f.filename and _allowed_file(f.filename):
            content = f.read().decode("utf-8", errors="replace")
            STATE[f.filename] = content
            added += 1

    if added == 0:
        flash("No valid .txt files were found in your upload.", "danger")
        return redirect(url_for("index"))

    flash(f"Successfully uploaded {added} policy document(s).", "success")
    return redirect(url_for("dashboard"))


@app.route("/load-sample", methods=["POST"])
def load_sample():
    """Load the bundled sample policy documents for an instant demo."""
    _load_sample_data()
    flash(f"Loaded {len(STATE)} sample policy documents.", "success")
    return redirect(url_for("dashboard"))


@app.route("/clear", methods=["POST"])
def clear_state():
    """Clear all currently loaded documents."""
    STATE.clear()
    flash("Cleared all loaded documents.", "info")
    return redirect(url_for("index"))


@app.route("/dashboard", methods=["GET"])
def dashboard():
    """Render the analysis dashboard for the currently loaded documents."""
    if not STATE:
        flash("No policy documents loaded yet. Upload files or load sample data first.", "warning")
        return redirect(url_for("index"))

    results = run_analysis(STATE)
    return render_template("dashboard.html", results=results)


@app.route("/report", methods=["GET"])
def report_preview():
    """Render an HTML preview of the report (in addition to the PDF export)."""
    if not STATE:
        flash("No policy documents loaded yet. Upload files or load sample data first.", "warning")
        return redirect(url_for("index"))

    results = run_analysis(STATE)
    return render_template("report.html", results=results)


@app.route("/report/pdf", methods=["GET"])
def report_pdf():
    """Generate and download the PDF version of the analysis report."""
    if not STATE:
        flash("No policy documents loaded yet. Upload files or load sample data first.", "warning")
        return redirect(url_for("index"))

    documents, conflicts, redundancies, stale_findings = get_internal_objects(STATE)
    pdf_bytes = generate_pdf_report(documents, conflicts, redundancies, stale_findings)

    from io import BytesIO

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="policy_analysis_report.pdf",
    )


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------

@app.route("/api/upload", methods=["POST"])
def api_upload():
    """REST endpoint: upload one or more .txt policy files.

    multipart/form-data with field name "policy_files" (one or more files).

    Returns:
        JSON list of the currently loaded filenames.
    """
    files = request.files.getlist("policy_files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided. Use form field 'policy_files'."}), 400

    added = []
    rejected = []
    for f in files:
        if f and f.filename and _allowed_file(f.filename):
            content = f.read().decode("utf-8", errors="replace")
            STATE[f.filename] = content
            added.append(f.filename)
        elif f and f.filename:
            rejected.append(f.filename)

    return jsonify(
        {
            "added": added,
            "rejected": rejected,
            "total_loaded": len(STATE),
            "loaded_files": sorted(STATE.keys()),
        }
    )


@app.route("/api/analyze", methods=["GET"])
def api_analyze():
    """REST endpoint: run full analysis on the currently loaded documents.

    Returns:
        JSON with documents, statements, conflicts, redundancies,
        staleness findings, graph data, and summary statistics.
    """
    if not STATE:
        return jsonify({"error": "No policy documents loaded. POST files to /api/upload first."}), 400

    results = run_analysis(STATE)
    return jsonify(results)


@app.route("/api/report", methods=["GET"])
def api_report():
    """REST endpoint: generate and return the PDF analysis report."""
    if not STATE:
        return jsonify({"error": "No policy documents loaded. POST files to /api/upload first."}), 400

    documents, conflicts, redundancies, stale_findings = get_internal_objects(STATE)
    pdf_bytes = generate_pdf_report(documents, conflicts, redundancies, stale_findings)

    from io import BytesIO

    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name="policy_analysis_report.pdf",
    )


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """REST endpoint: clear all currently loaded documents."""
    STATE.clear()
    return jsonify({"status": "cleared"})


@app.errorhandler(404)
def not_found(e):
    return render_template("index.html", loaded_files=sorted(STATE.keys())), 404


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
