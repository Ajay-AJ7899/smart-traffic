# Smart Traffic AI — Live Dashboard

A full-stack Django-based smart traffic operations platform for real-time traffic monitoring, AI-powered congestion prediction, peak-hour forecasting, interactive map visualization with congestion circles, and live route optimization — powered by **Geoapify**.

---

## 🖥️ Live Dashboard Preview

| Feature | What you see |
|---|---|
| **Live Traffic Map** | Geoapify dark map tiles over Bangalore with colored congestion circles |
| **Congestion Circles** | Semi-transparent radius circles (green/amber/red) sized by intensity |
| **Route on Map** | Blue polyline drawn from origin → destination via Geoapify Routing API |
| **AI Prediction** | 60-min congestion forecast with confidence bar |
| **Peak Hour Forecast** | 24-hour color-coded bar strip + chart + peak-hour pills |
| **Historical Feed** | Timestamped table of all traffic observations |

---

## ✨ Key Features

### 🗺️ Map & Visualization
- **Geoapify Dark Map** — dark-matter tile layer rendered with Leaflet.js
- **Congestion Intensity Circles** — `L.circle()` drawn at each known location; radius (500 m – 1.1 km) scales with real-time congestion intensity score
- **Real Route Polyline** — GeoJSON coordinates from Geoapify Routing API drawn as a blue `L.polyline` on the map
- **Start / End Markers** — green (origin) and red (destination) `L.circleMarker` with tooltips
- **Traffic Pin Layer** — solid colored dot on top of each congestion circle for precise location

### 📊 Peak Hour Forecast
- 24-element hourly congestion prediction for any location
- **Hour Strip** — compact mini-bar per hour, current hour highlighted, peak hours glow with animation
- **Bar Chart** — full Chart.js bar chart with Low/Medium/High color coding and tooltips
- **Worst / Best / Now stats** — instant summary header
- **Peak Period Pills** — shows which exact hours hit peak congestion today
- Falls back to a **seasonal day-of-week baseline** when historical data is sparse

### 🤖 Traffic Prediction (Time-Series)
- ARIMA model when ≥ 12 historical rows exist
- Seasonal baseline (hour-of-day × day-of-week) as robust fallback
- Returns: predicted level, estimated delay, confidence score, model version

### 🚦 Route Optimization
- **Geoapify** (default) — real geocoding + driving route with turn-by-turn steps
- **OpenRouteService** — alternative real routing provider
- **Google Routes API** — traffic-aware optimal routing
- **Offline fallback** — local distance/duration estimate when no API is reachable

### 🔔 Alerts
- Automatic high-congestion alert payload on `POST /traffic-data`
- Dashboard status pill switches to red "High Congestion Alert" mode

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend framework** | Django 5.0.6 |
| **REST API** | Django REST Framework 3.15.1 |
| **Database (dev)** | SQLite 3 |
| **Database (prod)** | PostgreSQL 16 |
| **ML / Prediction** | pandas, numpy, statsmodels (ARIMA), scikit-learn, joblib |
| **Map tiles** | Geoapify Dark-Matter via Leaflet.js 1.9.4 |
| **Routing API** | Geoapify Routing + Geocoding API |
| **Charts** | Chart.js (CDN) |
| **Static files** | WhiteNoise |
| **Production server** | Gunicorn |
| **CORS** | django-cors-headers |
| **Env config** | python-dotenv |
| **HTTP client** | requests |
| **Containerization** | Docker + Docker Compose |

---

## 📁 Project Structure

```
main-traffic/
├── .env                          # Environment variables (never commit secrets)
├── .env.example                  # Template for .env
├── manage.py                     # Django management entry point
├── requirements.txt              # Python dependencies
├── Dockerfile                    # Container image
├── docker-compose.yml            # Multi-service container setup
│
├── smart_traffic/                # Django project config
│   ├── settings.py               # Settings, DB, static files, maps config
│   ├── urls.py                   # Project-level URL routing
│   ├── wsgi.py                   # WSGI entry point
│   └── asgi.py                   # ASGI entry point
│
├── traffic/                      # Main Django app
│   ├── models.py                 # TrafficData + PredictionData models
│   ├── serializers.py            # DRF serializers and query validators
│   ├── views.py                  # All API views + dashboard view
│   ├── urls.py                   # App-level URL routing (6 endpoints)
│   ├── admin.py                  # Django admin registration
│   ├── apps.py                   # App config + SQLite pragmas
│   ├── tests.py                  # API test suite
│   │
│   ├── services/
│   │   ├── alerts.py             # High-congestion alert builder
│   │   ├── maps.py               # Geoapify / ORS / Google / offline routing
│   │   ├── prediction.py         # ARIMA + seasonal baseline predictor
│   │   └── peak_hours.py         # 24-hour peak forecast + intensity service
│   │
│   ├── migrations/               # Database migrations
│   └── management/commands/
│       ├── seed_traffic_data.py  # Demo data seeder
│       └── train_model.py        # ARIMA model trainer
│
├── templates/traffic/
│   └── dashboard.html            # Premium dark dashboard HTML
│
└── static/traffic/
    ├── css/dashboard.css         # Full dark-mode CSS (glassmorphism design)
    └── js/dashboard.js           # Leaflet map, charts, API calls, peak chart
```

---

## ⚙️ Environment Variables

Copy `.env.example` to `.env` and fill in your values:

```env
# Django core
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=
TIME_ZONE=Asia/Kolkata

# Database
DATABASE_ENGINE=sqlite
SQLITE_DB_PATH=runtime.sqlite3

# PostgreSQL (when DATABASE_ENGINE=postgres)
POSTGRES_DB=smart_traffic
POSTGRES_USER=smart_traffic
POSTGRES_PASSWORD=smart_traffic
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# Maps & Routing — set ONE provider
MAPS_PROVIDER=geoapify
GEOAPIFY_API_KEY=your-geoapify-api-key-here
OPENROUTESERVICE_API_KEY=
GOOGLE_MAPS_API_KEY=
MAPBOX_ACCESS_TOKEN=

# ML
ML_MIN_TRAINING_ROWS=12
```

### Maps provider options

| `MAPS_PROVIDER` | Required key | What it does |
|---|---|---|
| `geoapify` ✅ (default) | `GEOAPIFY_API_KEY` | Real geocoding + driving route + dark map tiles |
| `openrouteservice` | `OPENROUTESERVICE_API_KEY` | Free real routing alternative |
| `google` | `GOOGLE_MAPS_API_KEY` | Traffic-aware optimal routing via Google Routes API |
| `mapbox` | `MAPBOX_ACCESS_TOKEN` | Mapbox routing (placeholder — needs geocoding extension) |
| `offline` | _(none)_ | Local distance/duration estimate, no API calls |

---

## 🚀 How to Run Locally (Windows)

### Step 1 — Open the project folder

```powershell
cd D:\hackathon\django\main-traffic
```

### Step 2 — Activate the virtual environment

```powershell
.\venv\Scripts\activate
```

Or use Python directly without activating:

```powershell
.\venv\Scripts\python.exe --version
```

### Step 3 — Install dependencies

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Step 4 — Configure `.env`

Fastest local setup with Geoapify (already configured in this repo):

```env
DATABASE_ENGINE=sqlite
SQLITE_DB_PATH=runtime.sqlite3
MAPS_PROVIDER=geoapify
GEOAPIFY_API_KEY=your-geoapify-api-key
```

Get a **free** Geoapify API key at → https://myprojects.geoapify.com/

### Step 5 — Apply database migrations

```powershell
.\venv\Scripts\python.exe manage.py migrate
```

### Step 6 — Seed demo traffic data

```powershell
.\venv\Scripts\python.exe manage.py seed_traffic_data
```

This populates the database with realistic historical traffic observations for:
- MG Road
- Airport Road
- Outer Ring Road
- Electronic City

### Step 7 — (Optional) Create admin user

```powershell
.\venv\Scripts\python.exe manage.py shell -c "from django.contrib.auth import get_user_model; U=get_user_model(); u,_=U.objects.update_or_create(username='admin',defaults={'email':'admin@example.com','is_staff':True,'is_superuser':True,'is_active':True}); u.set_password('admin123'); u.save(); print('admin ready')"
```

### Step 8 — Run the development server

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

### Step 9 — Open in browser

| URL | What opens |
|---|---|
| `http://127.0.0.1:8000/` | 🗺️ Live dashboard |
| `http://127.0.0.1:8000/admin/` | 🔧 Django admin panel |
| `http://127.0.0.1:8000/peak-hours?location=MG+Road` | 📊 Raw peak-hour API |
| `http://127.0.0.1:8000/traffic-intensity` | 🔴 Raw intensity API |

---

### Run in Background (Windows — optional)

```powershell
$p = Start-Process `
  -FilePath '.\venv\Scripts\python.exe' `
  -ArgumentList 'manage.py','runserver','127.0.0.1:8000','--noreload' `
  -WorkingDirectory 'D:\hackathon\django\main-traffic' `
  -WindowStyle Hidden -PassThru
Write-Host "Server PID: $($p.Id)"
```

Stop it later:

```powershell
Stop-Process -Id <PID>
```

---

## 🐳 Docker (One-Command Start)

```powershell
copy .env.example .env
# Edit .env and fill in your Geoapify key
docker compose up --build
```

Opens at `http://127.0.0.1:8000/`

---

## 📡 API Endpoints

### `GET /`
Renders the premium dark dashboard.

---

### `GET /traffic-data`
List all traffic observations.

**Query params:**
| Param | Type | Description |
|---|---|---|
| `location` | string | Filter by location name (case-insensitive, partial match) |

**Example:**
```
GET /traffic-data?location=MG+Road
```

---

### `POST /traffic-data`
Submit a new traffic observation.

**Request body:**
```json
{
  "timestamp": "2026-04-22T09:00:00Z",
  "location": "MG Road",
  "congestion_level": "high",
  "avg_speed": 12.5,
  "incidents": "Accident near junction"
}
```

**Response** includes an `alert` payload when `congestion_level` is `high`.

---

### `GET /predict`
Predict congestion for a location.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `location` | string | required | Location name |
| `horizon_minutes` | int | `60` | How far ahead to predict (5–1440 min) |

**Example:**
```
GET /predict?location=MG+Road&horizon_minutes=60
```

**Response:**
```json
{
  "location": "MG Road",
  "predicted_congestion": "medium",
  "predicted_time": "2026-04-22T10:00:00+05:30",
  "estimated_delay_minutes": 15,
  "confidence": 0.78,
  "model_version": "arima-or-seasonal-baseline",
  "features": {
    "horizon_minutes": 60,
    "time_of_day": "10:00",
    "day_of_week": "Wednesday",
    "training_rows": 48
  }
}
```

---

### `GET /optimize-route`
Get the optimal driving route between two places.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `origin` | string | required | Starting location |
| `destination` | string | required | Ending location |
| `alternatives` | bool | `true` | Request alternative routes |

**Example:**
```
GET /optimize-route?origin=MG+Road&destination=Airport+Road
```

**Response:**
```json
{
  "provider": "geoapify",
  "origin": "MG Road",
  "destination": "Airport Road",
  "best_route": {
    "summary": "Real driving route",
    "distance_text": "10.2 km",
    "duration_text": "18 min",
    "duration_in_traffic_text": "18 min",
    "duration_in_traffic_seconds": 1080,
    "geometry": {
      "type": "LineString",
      "coordinates": [[12.975, 77.606], ...]
    },
    "steps": [
      "Drive east on Mahatma Gandhi Road",
      "Turn right onto Commissariat Road",
      "..."
    ]
  },
  "alternatives": [],
  "live_traffic_available": false,
  "real_route_available": true
}
```

---

### `GET /peak-hours` ⭐ New
Get 24-hour congestion forecast for a location.

**Query params:**
| Param | Type | Default | Description |
|---|---|---|---|
| `location` | string | `MG Road` | Location name |

**Example:**
```
GET /peak-hours?location=MG+Road
```

**Response:**
```json
{
  "location": "MG Road",
  "worst_hour": "08:00",
  "best_hour": "02:00",
  "peak_hours": ["08:00", "09:00", "17:00", "18:00"],
  "current_hour": {
    "hour": 14,
    "label": "14:00",
    "score": 1.5,
    "level": "low",
    "intensity": 0.25,
    "is_peak": false
  },
  "data_source": "historical",
  "hourly": [
    { "hour": 0, "label": "00:00", "score": 1.0, "level": "low", "intensity": 0.0, "is_peak": false },
    { "hour": 8, "label": "08:00", "score": 2.8, "level": "high", "intensity": 0.9, "is_peak": true },
    ...
  ]
}
```

---

### `GET /traffic-intensity` ⭐ New
Get current congestion intensity and map circle data for all known locations.

**Example:**
```
GET /traffic-intensity
```

**Response:**
```json
{
  "locations": [
    {
      "location": "MG Road",
      "lat": 12.9753,
      "lon": 77.6063,
      "level": "low",
      "score": 1.2,
      "intensity": 0.1,
      "radius_m": 550,
      "avg_speed": 45.5,
      "source": "live"
    },
    {
      "location": "Outer Ring Road",
      "lat": 12.9344,
      "lon": 77.6101,
      "level": "high",
      "score": 2.9,
      "intensity": 0.95,
      "radius_m": 1015,
      "avg_speed": 11.2,
      "source": "live"
    }
  ]
}
```

`radius_m` is used directly by the frontend to draw `L.circle()` on the Leaflet map.

---

## 🤖 Machine Learning — Prediction Details

Prediction lives in `traffic/services/prediction.py`.

### Flow

```
Request  →  Load historical rows for location
         →  If rows ≥ ML_MIN_TRAINING_ROWS (default 12):
               Fit ARIMA(1,0,1) on congestion score series
               Forecast 1 step ahead
            Else:
               Seasonal baseline (hour-of-day × day-of-week lookup)
         →  Map score (1.0–3.0) → level (low / medium / high)
         →  Estimate delay minutes
         →  Store PredictionData record
         →  Return JSON
```

### Train and persist a model artifact

```powershell
.\venv\Scripts\python.exe manage.py train_model --location "MG Road"
```

---

## 🗺️ Map Details — Geoapify Integration

### Tile layer
```
https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}.png?apiKey=YOUR_KEY
```

### Geocoding (address → lat/lon)
```
GET https://api.geoapify.com/v1/geocode/search
    ?text=MG Road, Bengaluru, Karnataka, India
    &format=json&limit=1&filter=countrycode:in
    &apiKey=YOUR_KEY
```

### Routing (lat/lon pairs → GeoJSON route)
```
GET https://api.geoapify.com/v1/routing
    ?waypoints=12.9753,77.6063|12.9591,77.6490
    &mode=drive
    &apiKey=YOUR_KEY
```

The returned GeoJSON `LineString` coordinates are passed directly to `L.polyline()`.

---

## 📊 Peak Hour Forecast Details

Lives in `traffic/services/peak_hours.py`.

| Data source | When used |
|---|---|
| Historical database | When ≥ 1 row exists for the location |
| Seasonal baseline | No data — uses hour-of-day × day-of-week pattern matrix |

The **hour profile** baseline reflects Bangalore rush hours:
- Morning peak: **08:00–09:00** (score 2.6–2.7)
- Evening peak: **17:00–18:00** (score 2.7–2.8)
- Quiet hours: **01:00–04:00** (score 1.0–1.1)

---

## 🔴 Congestion Intensity Circles

Lives in `traffic/services/peak_hours.py` → `all_locations_intensity()`.

| Congestion | Score | Circle fill opacity | Radius |
|---|---|---|---|
| Low | 1.0 | 12% | 500–650 m |
| Medium | 2.0 | 21% | 700–850 m |
| High | 3.0 | 30% | 950–1100 m |

Formula: `radius_m = base_radius × (0.5 + intensity)` where `intensity = (score - 1) / 2`.

---

## 🗄️ Database Models

### `TrafficData`
| Field | Type | Description |
|---|---|---|
| `timestamp` | DateTimeField | When observation was recorded |
| `location` | CharField | Location name (indexed) |
| `congestion_level` | CharField | `low` / `medium` / `high` |
| `avg_speed` | FloatField | Average speed in km/h |
| `incidents` | TextField | Incident description (optional) |

### `PredictionData`
| Field | Type | Description |
|---|---|---|
| `location` | CharField | Location name |
| `predicted_congestion` | CharField | Predicted level |
| `predicted_time` | DateTimeField | Time the prediction is for |
| `estimated_delay_minutes` | PositiveIntegerField | Delay estimate |
| `model_version` | CharField | Which model produced this |
| `created_at` | DateTimeField | Auto-set on creation |

---

## 🧪 Tests

```powershell
# Run all tests
.\venv\Scripts\python.exe manage.py test

# Run only traffic tests
.\venv\Scripts\python.exe manage.py test traffic.tests
```

---

## 🔧 Common Issues

### Port 8000 already in use

```powershell
Get-NetTCPConnection -LocalPort 8000
Stop-Process -Id <PID>
```

Or run on another port:

```powershell
.\venv\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

### Map shows no tiles

- Check `GEOAPIFY_API_KEY` in `.env` is valid
- Verify the key at https://myprojects.geoapify.com/
- Free plan allows 3 000 requests/day — sufficient for development

### Route optimization returns estimate instead of real route

- `real_route_available: false` means Geoapify geocoding or routing returned no result
- Verify the location names resolve correctly (they are appended with `, Bengaluru, Karnataka, India`)
- Check your Geoapify key has Routing API access enabled

### SQLite disk I/O error (Windows)

The app applies `PRAGMA journal_mode=OFF` automatically for SQLite on Windows to prevent rollback-journal write failures. If errors persist, switch to `SQLITE_DB_PATH=db.sqlite3`.

### `MAPS_PROVIDER` not picked up

Ensure `.env` is in the project root (same folder as `manage.py`) and `MAPS_PROVIDER=geoapify` is set without quotes.

---

## 🏗️ Production Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Use a strong random `DJANGO_SECRET_KEY`
- [ ] Switch to `DATABASE_ENGINE=postgres`
- [ ] Set `DJANGO_ALLOWED_HOSTS` to your domain only
- [ ] Configure `CORS_ALLOWED_ORIGINS`
- [ ] Serve behind HTTPS with a reverse proxy (nginx / Caddy)
- [ ] Run with Gunicorn: `gunicorn smart_traffic.wsgi:application`
- [ ] Never commit API keys — use environment secrets in your deployment platform
- [ ] Change or disable the demo admin password
- [ ] Run `python manage.py collectstatic` before deployment

---

## 🔑 Local Admin

```
URL:      http://127.0.0.1:8000/admin/
Username: admin
Password: admin123
```

> ⚠️ For local development only. Change the password before exposing to any network.

---

## 📜 License

MIT — free to use, modify, and distribute.
