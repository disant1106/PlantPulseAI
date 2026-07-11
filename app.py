import imghdr
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    url_for,
)
from werkzeug.utils import secure_filename

from database import (
    add_evaluation_sample,
    get_dashboard_metrics,
    get_evaluation_summary,
    get_reference_records,
    get_scan,
    get_scans,
    init_db,
    save_scan,
)
from services.ai_service import analyze_leaf_image
from services.report_service import create_report


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}


def load_env_file():
    env_path = BASE_DIR / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_env_file()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "plantpulse-local-dev")
app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024


def create_app():
    UPLOAD_DIR.mkdir(exist_ok=True)
    REPORT_DIR.mkdir(exist_ok=True)
    init_db()
    return app


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def detect_mime(file_storage, fallback):
    head = file_storage.stream.read(512)
    file_storage.stream.seek(0)
    kind = imghdr.what(None, head)
    if kind in {"jpeg", "png", "webp"}:
        return "image/jpeg" if kind == "jpeg" else f"image/{kind}"
    return fallback


def image_quality_warnings(image_bytes):
    warnings = []
    if len(image_bytes) < 50 * 1024:
        warnings.append("The image file is quite small, so fine leaf details may be hard to assess.")
    return warnings


def make_upload_filename(original_name):
    safe_name = secure_filename(original_name) or "leaf-image"
    ext = safe_name.rsplit(".", 1)[1].lower() if "." in safe_name else "jpg"
    stem = safe_name.rsplit(".", 1)[0][:60]
    stamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"{stamp}-{stem}-{uuid.uuid4().hex[:8]}.{ext}"


@app.route("/")
def index():
    return render_template("index.html", gemini_configured=bool(os.getenv("GEMINI_API_KEY")))


@app.route("/upload", methods=["POST"])
def upload():
    file = request.files.get("image")
    if not file or not file.filename:
        flash("Please upload a leaf image.", "error")
        return redirect(url_for("index"))

    if not allowed_file(file.filename):
        flash("Unsupported file format. Please upload JPG, PNG, or WebP.", "error")
        return redirect(url_for("index"))

    mime_type = detect_mime(file, file.mimetype)
    if mime_type not in ALLOWED_MIME_TYPES:
        flash("Invalid image file. Please upload a real JPG, PNG, or WebP image.", "error")
        return redirect(url_for("index"))

    image_bytes = file.read()
    if not image_bytes:
        flash("The uploaded image is empty.", "error")
        return redirect(url_for("index"))

    image_filename = make_upload_filename(file.filename)
    image_path = UPLOAD_DIR / image_filename
    image_path.write_bytes(image_bytes)

    quality_warnings = image_quality_warnings(image_bytes)
    reference_records = get_reference_records()
    ai_result = analyze_leaf_image(image_bytes, mime_type, quality_warnings, reference_records)
    analysis = ai_result["analysis"]

    scan_id = str(uuid.uuid4())
    scan = {
        "scan_id": scan_id,
        "image_filename": image_filename,
        "original_image_name": secure_filename(file.filename) or file.filename,
        "image_path": f"uploads/{image_filename}",
        "image_type": mime_type,
        "image_size": len(image_bytes),
        "upload_timestamp": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "plant_health_status": analysis["plant_health_status"],
        "probable_issue": analysis["probable_issue"],
        "severity": analysis["severity"],
        "confidence_estimate": analysis["confidence_estimate"],
        "symptoms": analysis["visible_symptoms"],
        "care_recommendations": analysis["care_recommendations"],
        "prevention_tips": analysis["prevention_tips"],
        "image_quality_note": analysis["image_quality_note"],
        "disclaimer": analysis["disclaimer"],
        "raw_ai_response": ai_result["raw_response"],
        "error_info": ai_result["error"],
    }
    save_scan(scan)

    if not ai_result["ok"]:
        flash(ai_result["error"], "warning")
    return redirect(url_for("result", scan_id=scan_id))


@app.route("/result/<scan_id>")
def result(scan_id):
    scan = get_scan(scan_id)
    if not scan:
        flash("Scan not found.", "error")
        return redirect(url_for("history"))
    return render_template("result.html", scan=scan)


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)


@app.route("/history")
def history():
    return render_template("history.html", scans=get_scans())


@app.route("/dashboard")
def dashboard():
    metrics = get_dashboard_metrics()
    return render_template("dashboard.html", metrics=metrics)


@app.route("/report/<scan_id>")
def report(scan_id):
    scan = get_scan(scan_id)
    if not scan:
        flash("Scan not found.", "error")
        return redirect(url_for("history"))
    filename, path = create_report(scan, REPORT_DIR)
    return send_file(path, as_attachment=True, download_name=filename, mimetype="text/plain")


@app.route("/evaluation")
def evaluation():
    return render_template("evaluation.html", summary=get_evaluation_summary())


@app.route("/evaluation/add", methods=["POST"])
def evaluation_add():
    expected = request.form.get("expected_label", "")
    predicted = request.form.get("predicted_label", "")
    allowed = {"Healthy", "Diseased", "Unclear"}
    if expected not in allowed or predicted not in allowed:
        flash("Expected and predicted labels must be Healthy, Diseased, or Unclear.", "error")
        return redirect(url_for("evaluation"))

    image_filename = request.form.get("image_filename", "").strip()
    if not image_filename:
        flash("Image filename is required.", "error")
        return redirect(url_for("evaluation"))

    add_evaluation_sample(
        {
            "image_filename": image_filename,
            "expected_label": expected,
            "predicted_label": predicted,
            "match_status": "Match" if expected == predicted else "Mismatch",
            "notes": request.form.get("notes", "").strip(),
            "evaluated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        }
    )
    flash("Demo evaluation sample saved.", "success")
    return redirect(url_for("evaluation"))


@app.errorhandler(413)
def too_large(_error):
    flash("Image is too large. Please upload a smaller file.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    create_app()
    app.run(debug=False, host="127.0.0.1", port=int(os.getenv("PORT", "5050")))
else:
    create_app()
