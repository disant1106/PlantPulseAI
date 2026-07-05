from pathlib import Path


def _list_block(title, items):
    if not items:
        return f"{title}: None listed\n"
    return f"{title}:\n" + "\n".join(f"- {item}" for item in items) + "\n"


def build_report(scan):
    return f"""LeafScan.ai Plant Health Report
=================================

Scan ID: {scan["scan_id"]}
Scan Date/Time: {scan["upload_timestamp"]}
Image: {scan["original_image_name"]}

Health Status: {scan["plant_health_status"]}
Probable Issue: {scan["probable_issue"]}
Severity: {scan["severity"]}
Confidence Estimate: {scan["confidence_estimate"]}

{_list_block("Visible Symptoms", scan["symptoms"])}
{_list_block("Care Recommendations", scan["care_recommendations"])}
{_list_block("Prevention Tips", scan["prevention_tips"])}
Image Quality Note:
{scan["image_quality_note"]}

Disclaimer:
{scan["disclaimer"]}
"""


def create_report(scan, reports_dir):
    Path(reports_dir).mkdir(parents=True, exist_ok=True)
    filename = f"leafscan-report-{scan['scan_id']}.txt"
    path = Path(reports_dir) / filename
    path.write_text(build_report(scan), encoding="utf-8")
    return filename, path
