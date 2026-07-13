# Machine Learning Based Surface Contamination Detection System

A production-ready full-stack web application that receives UV reflectance sensor data from an ESP32, stores it in Supabase PostgreSQL, trains multiple ML classifiers to predict surface contamination levels, and displays everything on a professional dark-mode dashboard.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Supabase Setup](#supabase-setup)
- [Environment Variables](#environment-variables)
- [Running the Application](#running-the-application)
- [ESP32 Connection](#esp32-connection)
- [API Documentation](#api-documentation)
- [Machine Learning](#machine-learning)
- [Render Deployment](#render-deployment)
- [Dashboard Pages](#dashboard-pages)
- [Future Improvements](#future-improvements)

---

## Project Overview

The system works in four stages:

1. **Collect** — An ESP32 with a GUVA-S12SD UV sensor continuously POSTs JSON readings to `POST /api/readings`.
2. **Label** — Users manually assign Clean / Dirty / Critical labels to readings via the Dataset page.
3. **Train** — An administrator clicks "Start Training". Four ML models are compared; the best is saved automatically.
4. **Predict** — Every new reading from the ESP32 is automatically classified in real time.

---

## Tech Stack

| Layer       | Technology                              |
|-------------|------------------------------------------|
| Frontend    | HTML5, CSS3, Vanilla JavaScript, Bootstrap 5, Chart.js |
| Backend     | Python 3.11, Flask 3, Flask-SQLAlchemy, Flask-CORS |
| ML          | scikit-learn (Random Forest, SVM, Decision Tree, Logistic Regression), joblib |
| Database    | Supabase PostgreSQL (via psycopg2)       |
| Deployment  | Render (Gunicorn WSGI)                   |
| Version Control | Git                                 |

---

## Project Structure

```
uv_system/
├── app.py                  # Application factory & entry point
├── config.py               # Environment-based configuration
├── database.py             # SQLAlchemy instance
├── models.py               # ORM model: UVReading
├── requirements.txt        # Python dependencies
├── Procfile                # Gunicorn start command for Render
├── render.yaml             # Render deployment manifest
├── .env.example            # Environment variable template
├── .gitignore
│
├── ml/
│   ├── dataset.py          # Dataset extraction & CSV export
│   ├── train.py            # Multi-model training pipeline
│   └── predict.py          # Inference engine with model cache
│
├── routes/
│   ├── api.py              # REST API Blueprint (/api/*)
│   └── dashboard.py        # HTML page routes Blueprint
│
├── templates/
│   ├── base.html           # Shared layout: sidebar, navbar, toasts
│   ├── dashboard.html      # Main dashboard with live stats
│   ├── index.html          # Live readings table with labelling
│   ├── dataset.html        # Dataset overview & feature stats
│   ├── training.html       # Model training & comparison
│   ├── prediction.html     # Manual prediction & history
│   ├── statistics.html     # Charts & aggregated statistics
│   └── settings.html       # Export, upload, reset controls
│
├── static/
│   ├── css/style.css       # Full dark-mode stylesheet
│   └── js/
│       ├── api.js          # Shared fetch helper & UI utilities
│       ├── charts.js       # Chart.js gauge & real-time chart
│       └── dashboard.js    # Dashboard polling controller
│
└── models/
    ├── .gitkeep
    ├── best_model.pkl      # Generated after training (gitignored)
    └── label_encoder.pkl   # Generated after training (gitignored)
```

---

## Installation

### Prerequisites

- Python 3.9 or higher
- pip
- A Supabase account (free tier works)
- Git

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/your-username/uv-contamination-system.git
cd uv-contamination-system/uv_system

# 2. Create and activate a virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy environment template
cp .env.example .env
# Then edit .env with your Supabase DATABASE_URL and secret key
```

---

## Supabase Setup

1. Go to [https://supabase.com](https://supabase.com) and create a new project.
2. Once the project is ready, navigate to **Settings → Database**.
3. Copy the **Connection string** (URI format). It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```
4. Paste it as `DATABASE_URL` in your `.env` file.
5. The application will **automatically create the `uv_readings` table** on first startup using SQLAlchemy's `create_all()`.

> **Note:** If you use Supabase's connection pooler (port 6543), use `?pgbouncer=true` or switch to the direct connection on port 5432.

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Required
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
FLASK_SECRET_KEY=your-long-random-secret-key

# Optional (defaults shown)
FLASK_ENV=development
FLASK_DEBUG=True
APP_HOST=0.0.0.0
APP_PORT=5000
MODEL_PATH=models/best_model.pkl
ENCODER_PATH=models/label_encoder.pkl
```

---

## Running the Application

```bash
# Development
python app.py

# Production (local test with Gunicorn)
gunicorn "app:create_app()" --bind 0.0.0.0:5000 --workers 2
```

Open your browser at `http://localhost:5000`.

---

## ESP32 Connection

Configure your ESP32 Arduino sketch to POST to your server URL.

### JSON Payload Format

```json
{
  "device_id":   "ESP32_UV_001",
  "uv_raw":      69,
  "uv_average":  70.68,
  "uv_min":      65,
  "uv_max":      78,
  "uv_range":    13,
  "voltage_mv":  199,
  "surface_type":"Plastic",
  "distance_cm": 3,
  "manual_label":"Clean"
}
```

### Minimal Arduino Sketch Snippet

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* ssid     = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* serverUrl = "https://your-app.onrender.com/api/readings";

void sendReading(float uvRaw, float uvAvg, float uvMin, float uvMax,
                 float uvRange, float voltage, float distance) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(serverUrl);
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["device_id"]    = "ESP32_UV_001";
  doc["uv_raw"]       = uvRaw;
  doc["uv_average"]   = uvAvg;
  doc["uv_min"]       = uvMin;
  doc["uv_max"]       = uvMax;
  doc["uv_range"]     = uvRange;
  doc["voltage_mv"]   = voltage;
  doc["surface_type"] = "Plastic";
  doc["distance_cm"]  = distance;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  http.end();
}
```

### Hardware

| Component        | ESP32 Pin |
|------------------|-----------|
| GUVA-S12SD OUT   | GPIO 34 (ADC) |
| UVA LED 1 Anode  | GPIO 25 (via 100Ω) |
| UVA LED 2 Anode  | GPIO 26 (via 100Ω) |
| GND              | GND       |
| 3.3V             | 3.3V      |

---

## API Documentation

All endpoints return JSON. Base URL: `http://localhost:5000` (or your Render URL).

### `GET /health`
System health check.
```json
{ "status": "ok", "database": "connected", "model_available": true, "timestamp": "..." }
```

### `GET /api/health`
Same as above, namespaced under `/api`.

### `GET /api/latest`
Returns the single most recent UV reading.

### `GET /api/readings`
Paginated list of all readings.

| Query Param | Type   | Default | Description                    |
|-------------|--------|---------|--------------------------------|
| `page`      | int    | 1       | Page number                    |
| `per_page`  | int    | 50      | Results per page (max 1000)    |
| `label`     | string | —       | Filter by `manual_label`       |
| `device_id` | string | —       | Filter by device               |
| `from_date` | ISO    | —       | Filter readings after date     |
| `to_date`   | ISO    | —       | Filter readings before date    |

### `POST /api/readings`
Ingest a new reading from the ESP32. Auto-predicts if model is ready.
```json
// Request body — ESP32 JSON payload
// Response
{ "success": true, "id": 42, "predicted_label": "Clean", "confidence": 0.94 }
```

### `PATCH /api/readings/<id>/label`
Assign or update a manual label.
```json
// Request
{ "label": "Dirty", "notes": "Visible dust on surface" }
// Response
{ "success": true, "id": 42, "label": "Dirty" }
```

### `GET /api/export`
Download CSV file.

| Query Param | Value              | Description               |
|-------------|-------------------|---------------------------|
| `type`      | `all` (default)   | All readings              |
| `type`      | `labelled`        | Only manually labelled    |

### `POST /api/train`
Train all four ML models and save the best.
```json
// Response
{
  "status": "success",
  "best_model": "Random Forest",
  "best_f1": 0.9667,
  "total_samples": 120,
  "train_samples": 96,
  "test_samples": 24,
  "classes": ["Clean", "Critical", "Dirty"],
  "trained_at": "2024-01-15T10:30:00+00:00",
  "model_results": { ... }
}
```

### `POST /api/predict`
Predict contamination for arbitrary input.
```json
// Request — same schema as POST /api/readings
// Response
{
  "predicted_label": "Clean",
  "confidence": 0.9412,
  "probabilities": { "Clean": 0.9412, "Dirty": 0.0451, "Critical": 0.0137 }
}
```

### `GET /api/statistics`
Aggregated statistics for charts and dashboard widgets.

### `DELETE /api/reset`
Delete all readings from the database. Irreversible.

### `POST /api/upload`
Upload a CSV file to bulk-import readings.
```
Content-Type: multipart/form-data
Field: file (CSV)
```

---

## Machine Learning

### Training Pipeline

1. Load all rows where `manual_label IS NOT NULL` from the database.
2. Extract feature columns: `uv_raw`, `uv_average`, `uv_min`, `uv_max`, `uv_range`, `voltage_mv`, `distance_cm`.
3. Encode labels with `LabelEncoder`.
4. Split 80% train / 20% test (stratified).
5. Train four classifiers in parallel:
   - **Random Forest** — 100 trees, balanced class weights
   - **Support Vector Machine** — RBF kernel, probability enabled
   - **Decision Tree** — max depth 10, balanced class weights
   - **Logistic Regression** — max_iter 1000, balanced class weights
6. Evaluate each with Accuracy, Precision, Recall, F1 (weighted), 5-fold CV.
7. Select the model with the highest weighted F1 score.
8. Retrain the winner on the full dataset.
9. Save `models/best_model.pkl` and `models/label_encoder.pkl`.

### Minimum Training Samples

At least **10 labelled readings** are required before training. For reliable models, aim for **50+ per class**.

### Label Classes

| Label    | Meaning                                 | Badge Colour |
|----------|-----------------------------------------|--------------|
| Clean    | Surface is uncontaminated               | Green        |
| Dirty    | Surface has light contamination         | Orange       |
| Critical | Heavy contamination, immediate action   | Red          |

---

## Render Deployment

### Steps

1. Push your code to GitHub:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin https://github.com/your-username/uv-contamination-system.git
   git push -u origin main
   ```

2. Go to [https://render.com](https://render.com) → **New Web Service**.

3. Connect your GitHub repository.

4. Render will auto-detect `render.yaml`. Confirm:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

5. Add environment variables in the Render dashboard:
   - `DATABASE_URL` — your Supabase connection string
   - `FLASK_SECRET_KEY` — a long random string
   - `FLASK_ENV` — `production`

6. Click **Deploy**. Your app will be live at `https://your-app.onrender.com`.

> **Free tier note:** Render free services spin down after 15 minutes of inactivity. The first request after idle may take ~30 seconds to wake up. Use a UptimeRobot ping to keep it alive if needed.

---

## Dashboard Pages

| Page        | URL            | Description                                     |
|-------------|----------------|-------------------------------------------------|
| Dashboard   | `/`            | Live stats, gauge, prediction circle, recent table |
| Live Readings | `/live`      | Full paginated table with label assignment      |
| Dataset     | `/dataset`     | Label distribution, feature statistics          |
| Train Model | `/training`    | Trigger training, view model comparison & confusion matrices |
| Prediction  | `/prediction`  | Manual predict form + recent predictions        |
| Statistics  | `/statistics`  | Charts: daily counts, avg UV trend, distributions |
| Settings    | `/settings`    | Export, upload, retrain, database reset         |

---

## Future Improvements

- **Real-time WebSocket push** — Replace polling with Flask-SocketIO for instant dashboard updates without HTTP overhead.
- **Multi-device support** — Per-device dashboards and individual model training.
- **Automated retraining** — Trigger retraining automatically when labelled sample count crosses a threshold.
- **Anomaly detection** — Add an Isolation Forest model to flag out-of-range readings as anomalies even without labels.
- **Time-series features** — Add rolling window statistics (last-N-reading mean/std) as ML features for improved accuracy.
- **User authentication** — Flask-Login or JWT auth to protect the training and reset endpoints.
- **Email / SMS alerts** — Notify administrators when a Critical reading is detected.
- **Model versioning** — Keep a history of trained models with timestamps and metrics for rollback.
- **MQTT support** — Accept readings over MQTT in addition to HTTP for lower-power ESP32 operation.
- **Mobile app** — React Native companion app for on-the-go monitoring.
