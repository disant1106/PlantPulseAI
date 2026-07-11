import base64
import json
import os
from copy import deepcopy

import requests


DEFAULT_ANALYSIS = {
    "plant_health_status": "Unclear",
    "probable_issue": "Unable to determine from the available image",
    "severity": "Unknown",
    "confidence_estimate": "Low",
    "visible_symptoms": [],
    "care_recommendations": [
        "Retake the photo in natural light with the affected leaf filling most of the frame.",
        "Inspect the plant for pests, discoloration, spots, wilting, or damaged edges.",
    ],
    "prevention_tips": [
        "Keep leaves dry when watering and remove badly damaged leaves.",
        "Monitor the plant regularly and isolate it if disease is suspected.",
    ],
    "image_quality_note": "The image could not be analyzed reliably.",
    "disclaimer": "This is an AI-assisted assessment and is not a replacement for expert agricultural advice.",
}


def _as_list(value):
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if not value:
        return []
    return [item.strip() for item in str(value).replace(";", "\n").splitlines() if item.strip()]


def normalize_analysis(data):
    analysis = deepcopy(DEFAULT_ANALYSIS)
    if isinstance(data, dict):
        analysis.update(data)

    if analysis["plant_health_status"] not in {"Healthy", "Diseased", "Unclear"}:
        analysis["plant_health_status"] = "Unclear"
    if analysis["severity"] not in {"Low", "Medium", "High", "Unknown"}:
        analysis["severity"] = "Unknown"

    analysis["visible_symptoms"] = _as_list(analysis.get("visible_symptoms"))
    analysis["care_recommendations"] = _as_list(analysis.get("care_recommendations"))
    analysis["prevention_tips"] = _as_list(analysis.get("prevention_tips"))
    analysis["disclaimer"] = analysis.get("disclaimer") or DEFAULT_ANALYSIS["disclaimer"]
    return analysis


def _extract_json(text):
    if not text:
        raise ValueError("Gemini returned an empty response.")
    clean = text.strip()
    if clean.startswith("```json"):
        clean = clean[7:].strip()
    if clean.startswith("```"):
        clean = clean[3:].strip()
    if clean.endswith("```"):
        clean = clean[:-3].strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Gemini did not return valid JSON.")
        return json.loads(clean[start : end + 1])


def _prompt(quality_warnings, reference_records):
    reference_summary = "\n".join(
        f"- {row['issue_name']} ({row['category']}): symptoms: {row['common_symptoms']}; care: {row['care_steps']}"
        for row in reference_records
    )
    warnings = " ".join(quality_warnings) if quality_warnings else "None detected."
    return f"""
You are PlantPulse AI, an AI vision assistant for plant health screening.
Analyze the uploaded leaf image using Gemini Vision. Return ONLY valid JSON.
Do not claim custom training, official model accuracy, or a verified diagnosis.

Required JSON fields:
{{
  "plant_health_status": "Healthy | Diseased | Unclear",
  "probable_issue": "fungal infection, nutrient deficiency, pest damage, water stress, leaf blight, healthy, or unclear",
  "severity": "Low | Medium | High | Unknown",
  "confidence_estimate": "percentage or descriptive confidence",
  "visible_symptoms": ["symptom"],
  "care_recommendations": ["practical step"],
  "prevention_tips": ["future prevention tip"],
  "image_quality_note": "whether image quality affects the result",
  "disclaimer": "AI-assisted and not a replacement for expert agricultural advice"
}}

If the photo does not clearly show a plant leaf, set plant_health_status to "Unclear".
Local image quality warnings: {warnings}

Supportive reference content, not a training dataset:
{reference_summary}
""".strip()


def analyze_leaf_image(image_bytes, mime_type, quality_warnings, reference_records):
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash").strip()

    if not api_key:
        fallback = normalize_analysis(
            {
                "image_quality_note": " ".join(quality_warnings)
                or "Gemini analysis was skipped because GEMINI_API_KEY is missing.",
            }
        )
        return {
            "ok": False,
            "analysis": fallback,
            "raw_response": "",
            "error": "Missing Gemini API key. Add GEMINI_API_KEY to your .env file.",
        }

    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {"text": _prompt(quality_warnings, reference_records)},
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64.b64encode(image_bytes).decode("ascii"),
                        }
                    },
                ],
            }
        ],
        "generationConfig": {"temperature": 0.2, "response_mime_type": "application/json"},
    }

    try:
        response = requests.post(
            endpoint,
            params={"key": api_key},
            json=payload,
            timeout=45,
        )
        response.raise_for_status()
        data = response.json()
        raw_text = "\n".join(
            part.get("text", "")
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
        ).strip()
        analysis = normalize_analysis(_extract_json(raw_text))
        if quality_warnings:
            analysis["image_quality_note"] = (
                f"{analysis['image_quality_note']} Local checks: {' '.join(quality_warnings)}"
            )
        return {"ok": True, "analysis": analysis, "raw_response": raw_text, "error": ""}
    except Exception as exc:
        fallback = normalize_analysis(
            {
                "image_quality_note": " ".join(quality_warnings)
                or "Gemini analysis was unavailable for this image.",
            }
        )
        return {"ok": False, "analysis": fallback, "raw_response": "", "error": str(exc)}
