# Smart Traffic Prediction Dashboard

Production-ready MVP for traffic ingestion, congestion prediction, alerts, route optimization, and a simple operations dashboard.

## Project Structure

```text
smart_traffic/
  settings.py          Django, DRF, PostgreSQL, static, Maps API config
  urls.py              Project URL routing
traffic/
  models.py            TrafficData and PredictionData models
  serializers.py       DRF serializers and query validators
  views.py             API and dashboard views
  services/
    alerts.py          Real-time high-congestion alert logic
    maps.py            Google Maps/Mapbox/offline route optimization service
    prediction.py      ARIMA forecasting with seasonal fallback
  management/commands/
    seed_traffic_data.py
    train_model.py     ARIMA training command
templates/traffic/
  dashboard.html       Dashboard shell
static/traffic/
  css/dashboard.css
  js/dashboard.js
```

## APIs

### `POST /traffic-data`

Stores real-time traffic input.

```json
{
  "timestamp": "2026-04-19T09:00:00Z",
  "location": "MG Road",
  "congestion_level": "high",
  "avg_speed": 18.5,
  "incidents": "Accident near junction"
}
```

High congestion rows return an `alert` payload.

### `GET /traffic-data`

Fetches historical traffic data. Optional filter:

```text
/traffic-data?location=MG Road
```

### `GET /predict`

Returns ML traffic prediction.

```text
/predict?location=MG Road&horizon_minutes=60
```

Response includes congestion level, predicted time, delay estimate, confidence, and feature metadata.

### `GET /optimize-route`

Returns a route suggestion.

```text
/optimize-route?origin=MG Road&destination=Airport Road
```

If `GOOGLE_MAPS_API_KEY` is configured, live traffic-aware Google Directions data is used. Otherwise an offline fallback response keeps the dashboard functional. The dashboard also loads a Google Maps JavaScript traffic layer when the key is present.

## Local Setup

1. Create and activate a virtual environment.

```bash
python -m venv .venv
.venv\Scripts\activate
```

If `python manage.py ...` says `No module named 'django'`, your terminal is using the wrong Python. On Windows, activate the existing project environment first:

```powershell
.\venv\Scripts\activate
python manage.py check
```

Or run commands explicitly with:

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

2. Install dependencies.

```bash
pip install -r requirements.txt
```

3. Copy environment variables.

```bash
copy .env.example .env
```

4. Choose a database.

For quick local development without PostgreSQL, set this in `.env`:

```text
DATABASE_ENGINE=sqlite
```

For PostgreSQL, keep `DATABASE_ENGINE=postgres`, start PostgreSQL, and update the `POSTGRES_*` values in `.env`.

5. Apply migrations and seed demo data.

```bash
python manage.py migrate
python manage.py seed_traffic_data
```

6. Run the app.

```bash
python manage.py runserver
```

Open `http://127.0.0.1:8000/`.

Run smoke tests:

```bash
python manage.py test
```

## Docker

```bash
copy .env.example .env
docker compose up --build
```

## Machine Learning

Prediction uses:

- historical traffic congestion observations
- time of day
- day of week
- recent average speed for delay estimation

The online predictor fits ARIMA when enough rows are available and falls back to a seasonal baseline when data is sparse. To train and persist a model artifact:

```bash
python manage.py seed_traffic_data
python manage.py train_model --location "MG Road"
```

## Environment Variables

```text
DJANGO_SECRET_KEY
DJANGO_DEBUG
DJANGO_ALLOWED_HOSTS
POSTGRES_DB
POSTGRES_USER
POSTGRES_PASSWORD
POSTGRES_HOST
POSTGRES_PORT
DATABASE_ENGINE
SQLITE_DB_PATH
MAPS_PROVIDER
GOOGLE_MAPS_API_KEY
MAPBOX_ACCESS_TOKEN
ML_MIN_TRAINING_ROWS
```

## Production Notes

- Set `DJANGO_DEBUG=False`.
- Use a strong `DJANGO_SECRET_KEY`.
- Restrict `DJANGO_ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`.
- Run behind HTTPS and a reverse proxy.
- Configure `GOOGLE_MAPS_API_KEY` for live route optimization and traffic-aware durations.
- Use a browser-restricted Google Maps key for the dashboard traffic layer, and a server-restricted key for backend route optimization in a hardened production deployment.
