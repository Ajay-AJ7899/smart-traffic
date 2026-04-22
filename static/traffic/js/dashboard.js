/* ══════════════════════════════════════════════
   Smart Traffic AI — Dashboard Logic
   Geoapify tiles + real route visualization
   ══════════════════════════════════════════════ */

"use strict";

// ── DOM refs ──────────────────────────────────
const tableBody          = document.querySelector("#traffic-table");
const predictionForm     = document.querySelector("#prediction-form");
const routeForm          = document.querySelector("#route-form");
const predictionCard     = document.querySelector("#prediction-card");
const predictedCongestion = document.querySelector("#predicted-congestion");
const estimatedDelay     = document.querySelector("#estimated-delay");
const predictionTime     = document.querySelector("#prediction-time");
const routeResult        = document.querySelector("#route-result");
const routeProvider      = document.querySelector("#route-provider");
const alertPill          = document.querySelector("#alert-pill");
const alertText          = document.querySelector("#alert-text");
const mapNode            = document.querySelector("#map");
const feedStatus         = document.querySelector("#feed-status");
const routeSteps         = document.querySelector("#route-steps");
const confidenceBar      = document.querySelector("#confidence-bar");
const confidencePct      = document.querySelector("#confidence-pct");
const loadingOverlay     = document.querySelector("#loading-overlay");
const centerBtn          = document.querySelector("#center-btn");
const mapSubtitle        = document.querySelector("#map-subtitle");

// ── Config ────────────────────────────────────
const REFRESH_MS     = 20000;
const BANGALORE_LATLNG = [12.9716, 77.5946];
const KNOWN_LOCATIONS  = {
  "mg road"         : [12.9753, 77.6063],
  "airport road"    : [12.9591, 77.6490],
  "outer ring road" : [12.9344, 77.6101],
  "outer ring"      : [12.9344, 77.6101],
  "electronic city" : [12.8390, 77.6770],
};

// ── State ─────────────────────────────────────
let trendChart     = null;
let routeMap       = null;
let routePolyline  = null;
let endpointMarkers = null;
let trafficMarkers  = [];
let currentLocation = "MG Road";
let lastTrafficRows = [];

// ── API Helpers ───────────────────────────────
async function fetchJson(url, options = {}) {
  const res  = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || data.error || `Error ${res.status}`;
    throw new Error(msg);
  }
  return data;
}

function escapeHtml(v) {
  return String(v)
    .replaceAll("&",  "&amp;")
    .replaceAll("<",  "&lt;")
    .replaceAll(">",  "&gt;")
    .replaceAll('"',  "&quot;")
    .replaceAll("'",  "&#039;");
}

function fmt(v) { return new Date(v).toLocaleString(); }

function fmtTime(v) {
  return new Date(v).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

// ── Leaflet Map Init ──────────────────────────
function initMap() {
  if (routeMap) return;

  const geoapifyKey = mapNode.dataset.geoapifyKey;
  const provider    = mapNode.dataset.provider;

  routeMap = L.map(mapNode, {
    center: BANGALORE_LATLNG,
    zoom: 12,
    zoomControl: true,
  });

  let tileUrl, attribution;

  if (provider === "geoapify" && geoapifyKey) {
    // Geoapify dark OSM-Bright tiles
    tileUrl = `https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}.png?apiKey=${geoapifyKey}`;
    attribution = '&copy; <a href="https://www.geoapify.com/">Geoapify</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>';
    if (mapSubtitle) mapSubtitle.textContent = "Geoapify Dark · Bangalore, India";
  } else {
    tileUrl = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
  }

  L.tileLayer(tileUrl, { attribution, maxZoom: 19 }).addTo(routeMap);

  centerBtn?.addEventListener("click", () => {
    routeMap.flyTo(BANGALORE_LATLNG, 12, { duration: 1 });
  });
}

// ── Traffic Markers ───────────────────────────
const CONGESTION_COLOR = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };

function buildCircleMarker(latlng, level, label) {
  const color = CONGESTION_COLOR[level] || "#3b82f6";
  return L.circleMarker(latlng, {
    radius: 10,
    color: "#050d1a",
    weight: 2,
    fillColor: color,
    fillOpacity: 0.92,
  }).bindTooltip(`<strong>${escapeHtml(label)}</strong><br>Congestion: <strong>${escapeHtml(level)}</strong>`, {
    sticky: true,
    className: "traffic-tooltip",
  });
}

function clearTrafficMarkers() {
  trafficMarkers.forEach(m => routeMap.removeLayer(m));
  trafficMarkers = [];
}

function drawTrafficMarkers(rows) {
  if (!routeMap) return;
  clearTrafficMarkers();

  // Aggregate latest congestion per location
  const latest = {};
  rows.forEach(row => {
    const key = row.location.toLowerCase();
    if (!latest[key]) latest[key] = row;
  });

  Object.entries(latest).forEach(([key, row]) => {
    const coords = KNOWN_LOCATIONS[key];
    if (!coords) return;
    const m = buildCircleMarker(coords, row.congestion_level, row.location);
    m.addTo(routeMap);
    trafficMarkers.push(m);
  });
}

// ── Route Drawing ─────────────────────────────
function clearRoute() {
  if (!routeMap) return;
  if (routePolyline)   { routeMap.removeLayer(routePolyline); routePolyline = null; }
  if (endpointMarkers) { routeMap.removeLayer(endpointMarkers); endpointMarkers = null; }
}

function drawRealRoute(data, origin, destination) {
  if (!routeMap) return false;
  const coords = data.best_route?.geometry?.coordinates || [];
  if (coords.length < 2) return false;

  clearRoute();

  // Animated dashed route line
  routePolyline = L.polyline(coords, {
    color: "#3b82f6",
    weight: 5,
    opacity: 0.9,
    lineJoin: "round",
    lineCap: "round",
  }).addTo(routeMap);

  const startPt = coords[0];
  const endPt   = coords[coords.length - 1];

  endpointMarkers = L.layerGroup([
    L.circleMarker(startPt, {
      radius: 9, color: "#050d1a", weight: 2,
      fillColor: "#10b981", fillOpacity: 1,
    }).bindTooltip(`<strong>Start:</strong> ${escapeHtml(origin)}`),
    L.circleMarker(endPt, {
      radius: 9, color: "#050d1a", weight: 2,
      fillColor: "#ef4444", fillOpacity: 1,
    }).bindTooltip(`<strong>End:</strong> ${escapeHtml(destination)}`),
  ]).addTo(routeMap);

  routeMap.fitBounds(routePolyline.getBounds(), { padding: [40, 40], maxZoom: 15 });
  return true;
}

// ── Table ─────────────────────────────────────
function renderRows(rows) {
  lastTrafficRows = rows;
  tableBody.innerHTML = rows.slice(0, 15).map(row => {
    const badgeCls  = `badge badge-${escapeHtml(row.congestion_level)}`;
    const incident  = row.incidents ? `<span style="color:#f59e0b">${escapeHtml(row.incidents)}</span>` : '<span style="color:#4a6a8a">—</span>';
    return `
      <tr>
        <td>${fmt(row.timestamp)}</td>
        <td><strong style="color:#e2eaf8">${escapeHtml(row.location)}</strong></td>
        <td><span class="${badgeCls}">${escapeHtml(row.congestion_level)}</span></td>
        <td>${row.avg_speed} km/h</td>
        <td>${incident}</td>
      </tr>`;
  }).join("");
}

// ── Chart ─────────────────────────────────────
function drawTrend(rows) {
  const canvas    = document.querySelector("#trend-chart");
  const latest    = rows.slice(0, 12).reverse();
  const labels    = latest.map(r => fmtTime(r.timestamp));
  const speeds    = latest.map(r => r.avg_speed);
  const incidents = latest.map(r => r.incidents ? 1 : 0);

  if (trendChart) { trendChart.destroy(); }

  trendChart = new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Avg Speed (km/h)",
          data: speeds,
          borderColor: "#3b82f6",
          backgroundColor: "rgba(59,130,246,0.1)",
          fill: true,
          tension: 0.4,
          yAxisID: "speed",
          pointRadius: 3,
          pointBackgroundColor: "#3b82f6",
        },
        {
          label: "Incident",
          data: incidents,
          borderColor: "#ef4444",
          backgroundColor: "#ef4444",
          pointRadius: 5,
          showLine: false,
          yAxisID: "incident",
        },
      ],
    },
    options: {
      responsive: true,
      animation: { duration: 600 },
      plugins: {
        legend: {
          display: true,
          position: "bottom",
          labels: { color: "#7b9fc9", font: { size: 11 }, boxWidth: 12, padding: 12 },
        },
        tooltip: {
          backgroundColor: "rgba(13,30,53,0.95)",
          borderColor: "rgba(99,160,255,0.3)",
          borderWidth: 1,
          titleColor: "#e2eaf8",
          bodyColor: "#7b9fc9",
          callbacks: {
            label(ctx) {
              if (ctx.dataset.yAxisID === "incident")
                return ctx.raw ? "⚠ Incident" : "✓ Clear";
              return `${ctx.raw} km/h`;
            },
          },
        },
      },
      scales: {
        speed: {
          beginAtZero: false,
          title: { display: true, text: "km/h", color: "#7b9fc9" },
          ticks: { color: "#7b9fc9", font: { size: 10 } },
          grid: { color: "rgba(99,160,255,0.06)" },
        },
        incident: { beginAtZero: true, display: false, max: 1, min: 0 },
        x: {
          ticks: { color: "#7b9fc9", font: { size: 10 }, maxRotation: 30 },
          grid: { color: "rgba(99,160,255,0.06)" },
        },
      },
    },
  });
}

// ── Prediction card update ────────────────────
const CONGESTION_GRAD = {
  low:    "linear-gradient(135deg, #10b981, #06b6d4)",
  medium: "linear-gradient(135deg, #f59e0b, #f97316)",
  high:   "linear-gradient(135deg, #ef4444, #dc2626)",
};

const CONGESTION_BORDER = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };

function updatePrediction(data) {
  const cong = data.predicted_congestion;
  predictedCongestion.textContent  = cong;
  predictedCongestion.style.backgroundImage = CONGESTION_GRAD[cong] || CONGESTION_GRAD.low;
  estimatedDelay.textContent = `⏱ ${data.estimated_delay_minutes} min estimated delay`;
  predictionCard.style.borderLeftColor = CONGESTION_BORDER[cong] || "#3b82f6";
  predictionTime.textContent = `${data.location} · ${fmtTime(data.predicted_time)}`;

  // Confidence bar
  const conf = Math.round((data.confidence || 0) * 100);
  if (confidenceBar) confidenceBar.style.width = `${conf}%`;
  if (confidencePct) confidencePct.textContent = `${conf}%`;

  // Alert pill
  if (cong === "high") {
    alertPill.className = "status-pill alert";
    alertText.textContent = "High Congestion Alert";
  } else {
    alertPill.className = "status-pill monitoring";
    alertText.textContent = "Monitoring";
  }
}

// ── Route Steps ───────────────────────────────
function renderSteps(steps) {
  if (!steps || !steps.length) {
    routeSteps.classList.add("hidden");
    return;
  }
  routeSteps.classList.remove("hidden");
  routeSteps.innerHTML = `<h4>Turn-by-turn directions</h4>` +
    steps.slice(0, 8).map((s, i) =>
      `<div class="step-item">
        <span class="step-num">${i + 1}</span>
        <span>${escapeHtml(s)}</span>
      </div>`
    ).join("");
}

// ── Load Dashboard Data ───────────────────────
async function loadDashboard(location = currentLocation) {
  currentLocation = location || "MG Road";
  const q = encodeURIComponent(currentLocation);

  try {
    const trafficPayload = await fetchJson(`/traffic-data?location=${q}`);
    const rows = trafficPayload.results || trafficPayload;
    renderRows(rows);
    drawTrend(rows);
    drawTrafficMarkers(rows);
    feedStatus.textContent = `${currentLocation} · refreshed ${fmtTime(new Date())}`;
  } catch (err) {
    feedStatus.textContent = `⚠ ${err.message}`;
  }

  try {
    const prediction = await fetchJson(`/predict?location=${q}&horizon_minutes=60`);
    updatePrediction(prediction);
  } catch (err) {
    predictedCongestion.textContent = "Error";
    estimatedDelay.textContent = err.message;
  }
}

// ── Event Listeners ───────────────────────────
predictionForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const loc = String(new FormData(predictionForm).get("location") || "").trim();
  if (!loc) return;
  predictedCongestion.textContent = "…";
  estimatedDelay.textContent = "Refreshing…";
  try {
    await loadDashboard(loc);
  } catch (err) {
    console.error(err);
  }
});

routeForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const fd   = new FormData(routeForm);
  const org  = String(fd.get("origin") || "").trim();
  const dest = String(fd.get("destination") || "").trim();
  if (!org || !dest) {
    routeResult.innerHTML = "<p style='color:#ef4444'>Enter both origin and destination.</p>";
    return;
  }

  routeResult.innerHTML = `<p style="color:#7b9fc9">🔄 Optimizing route via Geoapify…</p>`;
  routeSteps.classList.add("hidden");
  clearRoute();

  try {
    const data = await fetchJson(
      `/optimize-route?origin=${encodeURIComponent(org)}&destination=${encodeURIComponent(dest)}`
    );

    routeProvider.textContent = data.provider?.toUpperCase() || "GEOAPIFY";

    const r = data.best_route;
    const mapped = drawRealRoute(data, org, dest);

    routeResult.innerHTML = `
      <strong style="font-size:15px;color:#e2eaf8">${escapeHtml(r.summary || "Optimal Route")}</strong><br>
      <span style="color:#06b6d4;font-weight:600">🕒 ${escapeHtml(r.duration_in_traffic_text || r.duration_text || "—")}</span>
      &nbsp;·&nbsp;
      <span style="color:#7b9fc9">📍 ${escapeHtml(r.distance_text || "—")}</span>
      <br>
      <small style="color:${mapped ? '#10b981' : '#f59e0b'};margin-top:4px;display:block">
        ${mapped ? "✓ Route drawn on map" : "⚠ Estimating — no real geometry available"}
      </small>`;

    renderSteps(r.steps);
  } catch (err) {
    routeResult.innerHTML = `<p style="color:#ef4444">⚠ ${escapeHtml(err.message)}</p>`;
    clearRoute();
  }
});

// ── Initialise ────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
  initMap();

  try {
    await loadDashboard(currentLocation);
  } catch (err) {
    console.error("Dashboard init error:", err);
  } finally {
    if (loadingOverlay) {
      setTimeout(() => loadingOverlay.classList.add("hidden"), 400);
    }
  }

  // Trigger initial route to show map immediately
  const org  = document.querySelector("#origin-input")?.value || "MG Road";
  const dest = document.querySelector("#dest-input")?.value   || "Airport Road";
  try {
    const data = await fetchJson(
      `/optimize-route?origin=${encodeURIComponent(org)}&destination=${encodeURIComponent(dest)}`
    );
    drawRealRoute(data, org, dest);
  } catch (_) { /* silent — map still shows */ }
});

// Auto-refresh
setInterval(() => {
  loadDashboard(currentLocation).catch(err => {
    feedStatus.textContent = `⚠ Auto-refresh failed: ${err.message}`;
  });
}, REFRESH_MS);
