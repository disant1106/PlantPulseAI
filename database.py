import json
import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "plantpulse.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_id TEXT NOT NULL UNIQUE,
                image_filename TEXT NOT NULL,
                original_image_name TEXT NOT NULL,
                image_path TEXT NOT NULL,
                image_type TEXT NOT NULL,
                image_size INTEGER NOT NULL,
                upload_timestamp TEXT NOT NULL,
                plant_health_status TEXT NOT NULL,
                probable_issue TEXT NOT NULL,
                severity TEXT NOT NULL,
                confidence_estimate TEXT NOT NULL,
                symptoms TEXT NOT NULL,
                care_recommendations TEXT NOT NULL,
                prevention_tips TEXT NOT NULL,
                image_quality_note TEXT NOT NULL,
                disclaimer TEXT NOT NULL,
                raw_ai_response TEXT,
                error_info TEXT
            );

            CREATE TABLE IF NOT EXISTS evaluation_samples (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_filename TEXT NOT NULL,
                expected_label TEXT NOT NULL,
                predicted_label TEXT NOT NULL,
                match_status TEXT NOT NULL,
                notes TEXT,
                evaluated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS plant_reference (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                issue_name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                common_symptoms TEXT NOT NULL,
                possible_causes TEXT NOT NULL,
                care_steps TEXT NOT NULL,
                prevention_tips TEXT NOT NULL
            );
            """
        )
        seed_plant_reference(conn)


def seed_plant_reference(conn):
    records = [
        (
            "Fungal infection",
            "Disease",
            "Brown or black spots, powdery patches, yellow halos, spreading lesions",
            "Humid conditions, poor airflow, wet leaves, contaminated tools",
            "Remove badly affected leaves; improve airflow; avoid overhead watering; consider an appropriate fungicide if needed",
            "Water at soil level; space plants well; sanitize tools; inspect leaves weekly",
        ),
        (
            "Nutrient deficiency",
            "Nutrition",
            "Yellowing, pale leaves, interveinal chlorosis, weak growth",
            "Low nitrogen, iron, magnesium, incorrect soil pH, depleted potting mix",
            "Check soil pH; apply balanced fertilizer; correct specific deficiency when confirmed",
            "Use good soil; fertilize on schedule; avoid overwatering that leaches nutrients",
        ),
        (
            "Pest damage",
            "Pest",
            "Chewed edges, holes, sticky residue, webbing, speckled leaves",
            "Aphids, mites, caterpillars, beetles, scale insects",
            "Isolate plant; rinse leaves; remove visible pests; use insecticidal soap or neem when appropriate",
            "Inspect undersides of leaves; quarantine new plants; keep plants healthy and stress-free",
        ),
        (
            "Overwatering",
            "Water stress",
            "Yellow leaves, soft stems, wilting despite wet soil, dark root area",
            "Too frequent watering, poor drainage, compacted soil, oversized pot",
            "Let soil dry partially; improve drainage; remove rotted roots if repotting is needed",
            "Water only when the top soil is dry; use pots with drainage holes",
        ),
        (
            "Underwatering",
            "Water stress",
            "Crispy edges, drooping, dry soil, curled leaves",
            "Infrequent watering, heat stress, root-bound plant, fast-draining soil",
            "Water deeply; move from harsh sun temporarily; check whether repotting is needed",
            "Keep a consistent watering routine; mulch outdoor plants; monitor during hot weather",
        ),
        (
            "Leaf blight",
            "Disease",
            "Irregular brown patches, dead leaf tissue, rapid spread from leaf tips or margins",
            "Fungal or bacterial pathogens, wet foliage, infected debris",
            "Remove infected leaves; avoid splashing water; improve airflow; seek local extension guidance for severe cases",
            "Clear fallen leaves; rotate crops where relevant; water early in the day",
        ),
    ]
    conn.executemany(
        """
        INSERT OR IGNORE INTO plant_reference
        (issue_name, category, common_symptoms, possible_causes, care_steps, prevention_tips)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        records,
    )


def list_to_text(value):
    if isinstance(value, list):
        return json.dumps(value)
    if value is None:
        return json.dumps([])
    return json.dumps([str(value)])


def text_to_list(value):
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else [str(parsed)]
    except json.JSONDecodeError:
        return [value]


def row_to_scan(row):
    if row is None:
        return None
    scan = dict(row)
    scan["symptoms"] = text_to_list(scan.get("symptoms"))
    scan["care_recommendations"] = text_to_list(scan.get("care_recommendations"))
    scan["prevention_tips"] = text_to_list(scan.get("prevention_tips"))
    return scan


def save_scan(scan):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO scans (
                scan_id, image_filename, original_image_name, image_path, image_type,
                image_size, upload_timestamp, plant_health_status, probable_issue,
                severity, confidence_estimate, symptoms, care_recommendations,
                prevention_tips, image_quality_note, disclaimer, raw_ai_response, error_info
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                scan["scan_id"],
                scan["image_filename"],
                scan["original_image_name"],
                scan["image_path"],
                scan["image_type"],
                scan["image_size"],
                scan["upload_timestamp"],
                scan["plant_health_status"],
                scan["probable_issue"],
                scan["severity"],
                scan["confidence_estimate"],
                list_to_text(scan["symptoms"]),
                list_to_text(scan["care_recommendations"]),
                list_to_text(scan["prevention_tips"]),
                scan["image_quality_note"],
                scan["disclaimer"],
                scan.get("raw_ai_response", ""),
                scan.get("error_info", ""),
            ),
        )


def get_scan(scan_id):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
    return row_to_scan(row)


def get_scans(limit=None):
    sql = "SELECT * FROM scans ORDER BY upload_timestamp DESC"
    params = ()
    if limit:
        sql += " LIMIT ?"
        params = (limit,)
    with get_connection() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [row_to_scan(row) for row in rows]


def get_dashboard_metrics():
    with get_connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        status_rows = conn.execute(
            "SELECT plant_health_status, COUNT(*) AS count FROM scans GROUP BY plant_health_status"
        ).fetchall()
        severity_rows = conn.execute(
            "SELECT severity, COUNT(*) AS count FROM scans GROUP BY severity"
        ).fetchall()
        issue_rows = conn.execute(
            """
            SELECT probable_issue, COUNT(*) AS count
            FROM scans
            GROUP BY probable_issue
            ORDER BY count DESC, probable_issue ASC
            LIMIT 6
            """
        ).fetchall()

    status_counts = {"Healthy": 0, "Diseased": 0, "Unclear": 0}
    for row in status_rows:
        status_counts[row["plant_health_status"]] = row["count"]

    severity_counts = {"Low": 0, "Medium": 0, "High": 0, "Unknown": 0}
    for row in severity_rows:
        severity_counts[row["severity"]] = row["count"]

    return {
        "total": total,
        "status_counts": status_counts,
        "severity_counts": severity_counts,
        "common_issues": [dict(row) for row in issue_rows],
        "recent_scans": get_scans(limit=5),
    }


def add_evaluation_sample(sample):
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO evaluation_samples
            (image_filename, expected_label, predicted_label, match_status, notes, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                sample["image_filename"],
                sample["expected_label"],
                sample["predicted_label"],
                sample["match_status"],
                sample.get("notes", ""),
                sample["evaluated_at"],
            ),
        )


def get_evaluation_summary():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM evaluation_samples ORDER BY evaluated_at DESC").fetchall()
        total = conn.execute("SELECT COUNT(*) FROM evaluation_samples").fetchone()[0]
        correct = conn.execute(
            "SELECT COUNT(*) FROM evaluation_samples WHERE match_status = 'Match'"
        ).fetchone()[0]
    percentage = round((correct / total) * 100, 1) if total else 0
    return {
        "samples": [dict(row) for row in rows],
        "total": total,
        "correct": correct,
        "percentage": percentage,
    }


def get_reference_records():
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM plant_reference ORDER BY issue_name ASC").fetchall()
    return [dict(row) for row in rows]
