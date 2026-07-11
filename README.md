# PlantPulse AI v2.5

PlantPulse AI is an AI-powered plant health analysis web application that uses Gemini Vision/API to analyze leaf images, classify plant health status, estimate severity, generate care recommendations, store scan history in SQLite, and display dashboard insights.

This is an AI vision integration project. It does not train a custom deep learning model, and it does not report official model accuracy.

## Tech Stack

- Python Flask backend
- SQLite database
- HTML, CSS, and JavaScript frontend
- Chart.js dashboard charts
- Gemini Vision/API for image analysis

No Node.js, Express, Next.js, React, MongoDB, or custom-trained ML model is used.

## Features

- Leaf image upload with JPG, JPEG, PNG, and WebP validation
- Gemini Vision structured analysis
- Safe fallback if the API key is missing, Gemini fails, or JSON parsing fails
- Result page with uploaded image, health status, probable issue, severity, confidence estimate, symptoms, recommendations, prevention tips, image quality note, and disclaimer
- SQLite scan history
- Dashboard metrics from SQLite
- Downloadable text report per scan
- Small labelled demo evaluation mode
- Seeded `plant_reference` table for supportive common plant issue information
- Honest limitations and no fake accuracy claims

## Project Structure

```text
.
├── app.py
├── database.py
├── services/
│   ├── ai_service.py
│   └── report_service.py
├── templates/
├── static/
├── uploads/
├── reports/
├── plantpulse.db          # created automatically at runtime
├── requirements.txt
├── .env.example
└── README.md
```

## Database

SQLite tables are created automatically when the Flask app starts.

### `scans`

Stores every uploaded scan and AI result:

- `id`
- `scan_id`
- `image_filename`
- `original_image_name`
- `image_path`
- `image_type`
- `image_size`
- `upload_timestamp`
- `plant_health_status`
- `probable_issue`
- `severity`
- `confidence_estimate`
- `symptoms`
- `care_recommendations`
- `prevention_tips`
- `image_quality_note`
- `disclaimer`
- `raw_ai_response`
- `error_info`

### `evaluation_samples`

Stores small labelled demo evaluation records:

- `id`
- `image_filename`
- `expected_label`
- `predicted_label`
- `match_status`
- `notes`
- `evaluated_at`

### `plant_reference`

Stores supportive reference content for common plant issues:

- `id`
- `issue_name`
- `category`
- `common_symptoms`
- `possible_causes`
- `care_steps`
- `prevention_tips`

Seeded examples include fungal infection, nutrient deficiency, pest damage, overwatering, underwatering, and leaf blight.

Important: `plant_reference` is not an ML training dataset. Gemini Vision performs the image analysis.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your environment file:

```bash
cp .env.example .env
```

Add your Gemini API key:

```bash
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-1.5-flash
FLASK_SECRET_KEY=change_this_for_local_development
MAX_UPLOAD_MB=8
PORT=5050
```

Run locally:

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5050
```

## Routes

- `/` upload page
- `/upload` upload and analyze image
- `/result/<scan_id>` analysis result
- `/history` scan history from SQLite
- `/dashboard` dashboard metrics from SQLite
- `/report/<scan_id>` downloadable report
- `/evaluation` small labelled demo evaluation page
- `/evaluation/add` add evaluation sample

## Limitations

- Gemini Vision performs the analysis; this app does not train a plant disease model.
- Confidence is an AI confidence estimate, not official accuracy.
- The evaluation page is a small labelled demo workflow, not a scientific benchmark.
- SQLite is good for local demos and small projects, but production deployments may need PostgreSQL.
- AI plant health results should be reviewed by an expert for important agricultural decisions.

## Resume Bullet

Built PlantPulse AI, an AI-powered plant health assistant using Python Flask, SQLite, Chart.js, and Gemini Vision/API to analyze leaf images, classify plant health status, estimate severity, generate care recommendations, store scan history, and display dashboard insights.
