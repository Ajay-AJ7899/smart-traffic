# Smart Traffic Prediction Dashboard

A Django-based smart traffic operations dashboard for ingesting traffic observations, predicting congestion, showing high-congestion alerts, and suggesting routes with Google Maps, Mapbox, or an offline/local fallback.

## What This Project Does

- Shows a web dashboard at `http://127.0.0.1:8000/`
- Stores traffic observations such as location, congestion level, average speed, and incidents
- Predicts near-future congestion using ARIMA when enough history exists
- Falls back to a seasonal baseline when the dataset is small
- Returns alert payloads when high congestion is submitted
- Suggests routes using one of three modes:
  - Google Routes API, when `MAPS_PROVIDER=google` and `GOOGLE_MAPS_API_KEY` is configured
  - Mapbox placeholder mode, when `MAPS_PROVIDER=mapbox` and `MAPBOX_ACCESS_TOKEN` is configured
  - Offline/local estimate mode, when no live provider is reachable or configured
- Provides Django admin for managing traffic and prediction records

## Current Local Admin Login

The local development database has this admin user:

```text
URL: http://127.0.0.1:8000/admin/
Username: admin
Password: admin123
Email: admin@example.com
```

This is only for local development/demo use. Change the password before using this project outside your machine.

## Tech Stack

- Python 3.12
- Django 5.0.6
- Django REST Framework
- SQLite for local development
- PostgreSQL support through Docker or `.env`
- django-cors-headers for CORS configuration
- python-dotenv for environment variables
- requests for external Maps API calls
- pandas, numpy, statsmodels, scikit-learn, and joblib for prediction/model support
- Chart.js on the dashboard frontend
- WhiteNoise for static file serving
- Gunicorn for container/production-style serving

## Project Structure

```text
smart_traffic/
  settings.py          Django settings, database config, static files, maps config
  urls.py              Project URL routing
  wsgi.py              WSGI entry point
  asgi.py              ASGI entry point

traffic/
  admin.py             Django admin registration
  apps.py              App config and local SQLite connection setup
  models.py            TrafficData and PredictionData models
  serializers.py       DRF serializers and query validators
  views.py             API views and dashboard view
  services/
    alerts.py          High-congestion alert builder
    maps.py            Google/Mapbox/offline route suggestion service
    prediction.py      ARIMA plus seasonal fallback predictor
  management/commands/
    seed_traffic_data.py
    train_model.py
  tests.py             API tests

templates/traffic/
  dashboard.html       Dashboard HTML shell

static/traffic/
  css/dashboard.css    Dashboard styling
  js/dashboard.js      Dashboard API calls, charts, route UI, map loading
```

## Environment Variables

The app reads configuration from `.env`.

```text
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=
TIME_ZONE=Asia/Kolkata

POSTGRES_DB=smart_traffic
POSTGRES_USER=smart_traffic
POSTGRES_PASSWORD=smart_traffic
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

DATABASE_ENGINE=sqlite
SQLITE_DB_PATH=runtime.sqlite3

MAPS_PROVIDER=offline
GOOGLE_MAPS_API_KEY=
MAPBOX_ACCESS_TOKEN=

ML_MIN_TRAINING_ROWS=12
```

## How To Start Locally

### 1. Open the project folder

```powershell
cd D:\hackathon\django\main-traffic
```

### 2. Activate the virtual environment

If you are using the existing environment in this repo:

```powershell
.\venv\Scripts\activate
```

Or call Python directly without activating:

```powershell
.\venv\Scripts\python.exe manage.py check
```

### 3. Install dependencies if needed

```powershell
pip install -r requirements.txt
```

Or:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. Configure `.env`

For the fastest local demo, use SQLite and offline routing:

```text
DATABASE_ENGINE=sqlite
SQLITE_DB_PATH=runtime.sqlite3
MAPS_PROVIDER=offline
GOOGLE_MAPS_API_KEY=
MAPBOX_ACCESS_TOKEN=
```

If you want Google live routing, use:

```text
MAPS_PROVIDER=google
GOOGLE_MAPS_API_KEY=your-valid-google-routes-api-key
```

If you want Mapbox mode, use:

```text
MAPS_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=your-valid-mapbox-token
```

### 5. Apply migrations

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### 6. Seed demo traffic data

```powershell
.\venv\Scripts\python.exe manage.py seed_traffic_data
```

### 7. Create or reset the admin user

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; User=get_user_model(); user, _ = User.objects.update_or_create(username='admin', defaults={'email':'admin@example.com','is_staff':True,'is_superuser':True,'is_active':True}); user.set_password('admin123'); user.save(); print('admin ready')"
```

### 8. Run the server

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Open:

```text
Dashboard: http://127.0.0.1:8000/
Admin:     http://127.0.0.1:8000/admin/
```

## How To Start In The Background On Windows

Use this if you want the terminal/chat to return immediately:

```powershell
$p = Start-Process -FilePath '.\venv\Scripts\python.exe' -ArgumentList 'manage.py','runserver','127.0.0.1:8000','--noreload' -WorkingDirectory 'D:\hackathon\django\main-traffic' -WindowStyle Hidden -PassThru
$p.Id
```

Stop it later with:

```powershell
Stop-Process -Id <PROCESS_ID>
```

## API Endpoints

### Dashboard

```text
GET /
```

Renders the traffic dashboard.

### List traffic data

```text
GET /traffic-data
GET /traffic-data?location=MG Road
```

Returns stored traffic observations.

### Create traffic data

```text
POST /traffic-data
```

Example request:

```json
{
  "timestamp": "2026-04-19T09:00:00Z",
  "location": "MG Road",
  "congestion_level": "high",
  "avg_speed": 18.5,
  "incidents": "Accident near junction"
}
```

If the congestion level is `high`, the response includes an `alert` payload.

### Predict congestion

```text
GET /predict?location=MG%20Road&horizon_minutes=60
```

Returns:

- predicted congestion level
- predicted time
- estimated delay
- confidence score
- model metadata
- feature metadata

### Optimize route

```text
GET /optimize-route?origin=MG%20Road&destination=Airport%20Road
```

Returns:

- provider used
- origin
- destination
- best route summary
- distance
- duration
- live traffic availability
- alternatives, if the provider returns them

## What The Mapbox Access Token Is For

`MAPBOX_ACCESS_TOKEN` is for using Mapbox as an alternate map/routing provider instead of Google.

In this project, the maps service checks:

```text
MAPS_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=...
```

When both are set, route requests go through the Mapbox branch in `traffic/services/maps.py`.

Important current behavior:

- Google mode is the more complete live-routing implementation in this codebase.
- Mapbox mode currently returns a placeholder response saying Mapbox optimization requires geocoded coordinates.
- To make Mapbox fully live, the app would need an extra geocoding step that converts addresses like `MG Road` and `Airport Road` into longitude/latitude coordinates, then calls the Mapbox Directions or Optimization API.

So the token is useful if you want to extend the project from Google-based live routing to Mapbox-based routing.

## Routing Modes

### Offline mode

Use this for demos when internet/API access is unreliable:

```text
MAPS_PROVIDER=offline
GOOGLE_MAPS_API_KEY=
MAPBOX_ACCESS_TOKEN=
```

The app returns local estimated distance and duration.

### Google mode

Use this for live Google traffic-aware routing:

```text
MAPS_PROVIDER=google
GOOGLE_MAPS_API_KEY=your-valid-google-routes-api-key
```

Google mode calls:

```text
https://routes.googleapis.com/directions/v2:computeRoutes
```

If Google is unreachable, invalid, blocked by proxy, or returns an error, the app falls back to a local estimate.

### Mapbox mode

Use this when extending the project for Mapbox:

```text
MAPS_PROVIDER=mapbox
MAPBOX_ACCESS_TOKEN=your-valid-mapbox-token
```

The current implementation has a placeholder because Mapbox routing needs coordinates, not just plain address names.

## Machine Learning

Prediction is handled in `traffic/services/prediction.py`.

It uses:

- historical congestion values
- timestamp history
- time of day
- day of week
- recent average speed

Prediction flow:

1. Load historical rows for the requested location.
2. If enough rows exist, fit an ARIMA model.
3. If there is not enough data or ARIMA fails, use a seasonal baseline.
4. Convert the predicted numeric score into `low`, `medium`, or `high`.
5. Estimate delay minutes.
6. Store the prediction in `PredictionData`.

Train and persist a model artifact:

```powershell
.\venv\Scripts\python.exe manage.py train_model --location "MG Road"
```

## Database

Local development uses SQLite:

```text
DATABASE_ENGINE=sqlite
SQLITE_DB_PATH=runtime.sqlite3
```

PostgreSQL is supported through:

```text
DATABASE_ENGINE=postgres
POSTGRES_DB=smart_traffic
POSTGRES_USER=smart_traffic
POSTGRES_PASSWORD=smart_traffic
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

## Docker

The Docker setup includes:

- PostgreSQL 16 Alpine
- Django web service
- Gunicorn server

Run:

```powershell
copy .env.example .env
docker compose up --build
```

Then open:

```text
http://127.0.0.1:8000/
```

## Tests

Run all tests:

```powershell
.\venv\Scripts\python.exe manage.py test
```

Run only traffic API tests:

```powershell
.\venv\Scripts\python.exe manage.py test traffic.tests
```

## Common Issues

### Route suggestion says Google is unavailable

This means the app tried Google live routing, but the request failed. Common reasons:

- invalid API key
- Google Routes API not enabled
- billing not enabled in Google Cloud
- internet/proxy issue
- local environment points HTTPS traffic to a dead proxy such as `127.0.0.1:9`

For a demo, switch to:

```text
MAPS_PROVIDER=offline
GOOGLE_MAPS_API_KEY=
```

### SQLite disk I/O error

On this Windows workspace, SQLite rollback journal writes may fail. The app config applies:

```sql
PRAGMA journal_mode=OFF;
```

for SQLite connections to keep local development working.

### Port 8000 already in use

Find the process:

```powershell
Get-NetTCPConnection -LocalPort 8000
```

Stop the process:

```powershell
Stop-Process -Id <PROCESS_ID>
```

Or run on another port:

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

## Production Notes

- Set `DJANGO_DEBUG=False`.
- Use a strong `DJANGO_SECRET_KEY`.
- Do not commit real API keys.
- Use PostgreSQL instead of SQLite.
- Restrict `DJANGO_ALLOWED_HOSTS`.
- Configure `CORS_ALLOWED_ORIGINS`.
- Run behind HTTPS.
- Use Gunicorn plus a reverse proxy.
- Use separate restricted keys for browser maps and server-side routing.
- Change or remove the demo admin login.
