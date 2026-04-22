/* ══════════════════════════════════════════════
   Smart Traffic AI — Dashboard Logic v2
   · Geoapify tiles + real route visualization
   · Congestion circles (intensity radius)
   · 24-hour peak-hour forecast chart + strip
   ══════════════════════════════════════════════ */

"use strict";

// ── DOM refs ─────────────────────────────────
const tableBody           = document.querySelector("#traffic-table");
const predictionForm      = document.querySelector("#prediction-form");
const routeForm           = document.querySelector("#route-form");
const predictionCard      = document.querySelector("#prediction-card");
const predictedCongestion = document.querySelector("#predicted-congestion");
const estimatedDelay      = document.querySelector("#estimated-delay");
const predictionTime      = document.querySelector("#prediction-time");
const routeResult         = document.querySelector("#route-result");
const routeProvider       = document.querySelector("#route-provider");
const alertPill           = document.querySelector("#alert-pill");
const alertText           = document.querySelector("#alert-text");
const mapNode             = document.querySelector("#map");
const feedStatus          = document.querySelector("#feed-status");
const routeSteps          = document.querySelector("#route-steps");
const confidenceBar       = document.querySelector("#confidence-bar");
const confidencePct       = document.querySelector("#confidence-pct");
const loadingOverlay      = document.querySelector("#loading-overlay");
const centerBtn           = document.querySelector("#center-btn");
const mapSubtitle         = document.querySelector("#map-subtitle");
// Peak hour refs
const peakSubtitle        = document.querySelector("#peak-subtitle");
const worstHourEl         = document.querySelector("#worst-hour");
const bestHourEl          = document.querySelector("#best-hour");
const nowLevelEl          = document.querySelector("#now-level");
const hourStrip           = document.querySelector("#hour-strip");
const peakPills           = document.querySelector("#peak-pills");

// ── Config ───────────────────────────────────
const REFRESH_MS       = 20_000;
const BANGALORE        = [12.9716, 77.5946];

const KNOWN_LATLNG = {
  "mg road"        : [12.9753, 77.6063],
  "airport road"   : [12.9591, 77.6490],
  "outer ring road": [12.9344, 77.6101],
  "outer ring"     : [12.9344, 77.6101],
  "electronic city": [12.8390, 77.6770],
};

const CONG_COLOR = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };

// ── State ────────────────────────────────────
let trendChart        = null;
let peakChart         = null;
let routeMap          = null;
let routePolyline     = null;
let endpointMarkers   = null;
let trafficPinGroup   = null;   // circle markers (small pins)
let intensityCircles  = [];     // bigger semi-transparent circles
let currentLocation   = "MG Road";

// ── Utilities ────────────────────────────────
async function fetchJson(url, opts = {}) {
  const res  = await fetch(url, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || data.error || `Error ${res.status}`);
  return data;
}

function esc(v) {
  return String(v)
    .replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;")
    .replaceAll('"',"&quot;").replaceAll("'","&#039;");
}

function fmtDate(v) { return new Date(v).toLocaleString(); }
function fmtTime(v) { return new Date(v).toLocaleTimeString([], { hour:"2-digit", minute:"2-digit" }); }

// ══════════════════════════════════════════════
// MAP
// ══════════════════════════════════════════════
function initMap() {
  if (routeMap) return;

  const geoKey   = mapNode.dataset.geoapifyKey;
  const provider = mapNode.dataset.provider;

  routeMap = L.map(mapNode, { center: BANGALORE, zoom: 12, zoomControl: true });

  let tileUrl, attribution;
  if (provider === "geoapify" && geoKey) {
    tileUrl     = `https://maps.geoapify.com/v1/tile/dark-matter/{z}/{x}/{y}.png?apiKey=${geoKey}`;
    attribution = '&copy; <a href="https://www.geoapify.com/">Geoapify</a> | &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>';
    if (mapSubtitle) mapSubtitle.textContent = "Geoapify Dark · Bangalore, India";
  } else {
    tileUrl     = "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png";
    attribution = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';
  }

  L.tileLayer(tileUrl, { attribution, maxZoom: 19 }).addTo(routeMap);
  centerBtn?.addEventListener("click", () => routeMap.flyTo(BANGALORE, 12, { duration: 1 }));
}

// ── Route drawing ─────────────────────────────
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

  routePolyline = L.polyline(coords, {
    color: "#3b82f6", weight: 5, opacity: 0.9, lineJoin: "round", lineCap: "round",
  }).addTo(routeMap);

  const s = coords[0], e = coords[coords.length - 1];
  endpointMarkers = L.layerGroup([
    L.circleMarker(s, { radius: 9, color: "#050d1a", weight: 2, fillColor: "#10b981", fillOpacity: 1 })
      .bindTooltip(`<strong>Start:</strong> ${esc(origin)}`),
    L.circleMarker(e, { radius: 9, color: "#050d1a", weight: 2, fillColor: "#ef4444", fillOpacity: 1 })
      .bindTooltip(`<strong>End:</strong> ${esc(destination)}`),
  ]).addTo(routeMap);

  routeMap.fitBounds(routePolyline.getBounds(), { padding: [40, 40], maxZoom: 15 });
  return true;
}

// ── Congestion circles (intensity) ───────────
function clearIntensityCircles() {
  intensityCircles.forEach(c => routeMap.removeLayer(c));
  intensityCircles = [];
  if (trafficPinGroup) { routeMap.removeLayer(trafficPinGroup); trafficPinGroup = null; }
}

function drawIntensityCircles(locations) {
  if (!routeMap) return;
  clearIntensityCircles();

  const pins = [];

  locations.forEach(loc => {
    const color   = CONG_COLOR[loc.level] || "#3b82f6";
    const latLng  = [loc.lat, loc.lon];

    // ① Big translucent pulsing area circle
    const circle = L.circle(latLng, {
      radius:      loc.radius_m,
      color:       color,
      weight:      1.5,
      opacity:     0.6,
      fillColor:   color,
      fillOpacity: 0.12 + loc.intensity * 0.18,  // 0.12–0.30
    });

    // Popup with details
    circle.bindPopup(`
      <div style="min-width:160px">
        <strong style="font-size:14px">${esc(loc.location)}</strong><br>
        <span style="text-transform:capitalize;font-weight:600;color:${color}">${esc(loc.level)} congestion</span><br>
        <small>Intensity score: ${loc.score}/3.0</small><br>
        ${loc.avg_speed != null ? `<small>Avg speed: ${loc.avg_speed} km/h</small>` : ""}
        <br><small style="color:#7b9fc9">Source: ${esc(loc.source)}</small>
      </div>
    `, { className: "traffic-popup" });

    circle.addTo(routeMap);
    intensityCircles.push(circle);

    // ② Small solid pin on top
    const pin = L.circleMarker(latLng, {
      radius: 7, color: "#050d1a", weight: 2,
      fillColor: color, fillOpacity: 1,
    }).bindTooltip(
      `<strong>${esc(loc.location)}</strong> — ${esc(loc.level)}`,
      { sticky: true }
    );
    pins.push(pin);
  });

  trafficPinGroup = L.layerGroup(pins).addTo(routeMap);
}

// ══════════════════════════════════════════════
// PEAK HOUR FORECAST
// ══════════════════════════════════════════════
function renderHourStrip(hourly) {
  if (!hourStrip) return;
  const currentHour = new Date().getHours();

  hourStrip.innerHTML = hourly.map(h => {
    const pct    = Math.round((h.score - 1.0) / 2.0 * 100);   // 0–100%
    const barH   = Math.max(4, Math.round(pct * 0.4));         // 4–40 px
    const isNow  = h.hour === currentHour;
    const nowCls = isNow ? " is-now" : "";
    const peakCls = h.is_peak ? " is-peak" : "";
    return `
      <div class="hour-cell${nowCls}" title="${h.label} — ${h.level} (score ${h.score})">
        <div class="hc-bar-wrap">
          <div class="hc-bar ${h.level}${peakCls}" style="height:${barH}px"></div>
        </div>
        <span class="hc-label${nowCls}">${h.label}</span>
        <span class="hc-score">${h.score.toFixed(1)}</span>
      </div>`;
  }).join("");
}

function renderPeakChart(hourly) {
  const canvas = document.querySelector("#peak-chart");
  if (!canvas) return;

  const labels = hourly.map(h => h.label);
  const scores = hourly.map(h => h.score);
  const colors = hourly.map(h =>
    h.level === "high"   ? "rgba(239,68,68,0.85)"  :
    h.level === "medium" ? "rgba(245,158,11,0.75)" :
                           "rgba(16,185,129,0.65)"
  );
  const borderColors = hourly.map(h =>
    h.level === "high"   ? "#ef4444" :
    h.level === "medium" ? "#f59e0b" :
                           "#10b981"
  );

  if (peakChart) peakChart.destroy();

  peakChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Congestion Score",
        data: scores,
        backgroundColor: colors,
        borderColor: borderColors,
        borderWidth: 1,
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      animation: { duration: 800 },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: "rgba(13,30,53,0.95)",
          borderColor: "rgba(99,160,255,0.3)",
          borderWidth: 1,
          titleColor: "#e2eaf8",
          bodyColor: "#7b9fc9",
          callbacks: {
            title: ctx => ctx[0].label,
            label: ctx => {
              const h = hourly[ctx.dataIndex];
              return [`Score: ${h.score.toFixed(2)}`, `Level: ${h.level}`, h.is_peak ? "⚡ Peak hour" : ""];
            },
          },
        },
        annotation: undefined,
      },
      scales: {
        x: {
          ticks: { color: "#4a6a8a", font: { size: 9 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
          grid: { color: "rgba(99,160,255,0.05)" },
        },
        y: {
          min: 0.8, max: 3.2,
          ticks: {
            color: "#4a6a8a", font: { size: 10 },
            callback: v => v === 1 ? "Low" : v === 2 ? "Med" : v === 3 ? "High" : "",
            stepSize: 1,
          },
          grid: { color: "rgba(99,160,255,0.07)" },
        },
      },
    },
  });
}

function renderPeakMeta(data) {
  if (worstHourEl) worstHourEl.textContent = data.worst_hour;
  if (bestHourEl)  bestHourEl.textContent  = data.best_hour;
  if (nowLevelEl) {
    const lvl = data.current_hour?.level || "—";
    nowLevelEl.textContent  = lvl.charAt(0).toUpperCase() + lvl.slice(1);
    nowLevelEl.style.color  = CONG_COLOR[lvl] || "var(--text-primary)";
  }
  if (peakSubtitle) {
    peakSubtitle.textContent = `${esc(data.location)} · ${data.data_source === "historical" ? "from historical data" : "seasonal baseline"}`;
  }
  if (peakPills) {
    peakPills.innerHTML = (data.peak_hours || []).map(h =>
      `<span class="peak-pill">${esc(h)}</span>`
    ).join("") || `<span style="color:var(--text-muted);font-size:12px">No peak hours detected today</span>`;
  }
}

async function loadPeakForecast(location) {
  try {
    const data = await fetchJson(`/peak-hours?location=${encodeURIComponent(location)}`);
    renderHourStrip(data.hourly);
    renderPeakChart(data.hourly);
    renderPeakMeta(data);
  } catch (err) {
    if (peakSubtitle) peakSubtitle.textContent = `⚠ ${err.message}`;
  }
}

async function loadIntensityCircles() {
  try {
    const data = await fetchJson("/traffic-intensity");
    drawIntensityCircles(data.locations || []);
  } catch (err) {
    console.warn("Intensity circles:", err.message);
  }
}

// ══════════════════════════════════════════════
// TABLE + TREND CHART
// ══════════════════════════════════════════════
function renderRows(rows) {
  tableBody.innerHTML = rows.slice(0, 15).map(row => {
    const bc  = `badge badge-${esc(row.congestion_level)}`;
    const inc = row.incidents
      ? `<span style="color:#f59e0b">${esc(row.incidents)}</span>`
      : `<span style="color:#4a6a8a">—</span>`;
    return `
      <tr>
        <td>${fmtDate(row.timestamp)}</td>
        <td><strong style="color:#e2eaf8">${esc(row.location)}</strong></td>
        <td><span class="${bc}">${esc(row.congestion_level)}</span></td>
        <td>${row.avg_speed} km/h</td>
        <td>${inc}</td>
      </tr>`;
  }).join("");
}

function drawTrend(rows) {
  const canvas = document.querySelector("#trend-chart");
  const latest = rows.slice(0, 12).reverse();
  const labels = latest.map(r => fmtTime(r.timestamp));
  const speeds = latest.map(r => r.avg_speed);
  const incs   = latest.map(r => r.incidents ? 1 : 0);

  if (trendChart) trendChart.destroy();

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
          fill: true, tension: 0.4, yAxisID: "speed",
          pointRadius: 3, pointBackgroundColor: "#3b82f6",
        },
        {
          label: "Incident",
          data: incs,
          borderColor: "#ef4444", backgroundColor: "#ef4444",
          pointRadius: 5, showLine: false, yAxisID: "incident",
        },
      ],
    },
    options: {
      responsive: true, animation: { duration: 600 },
      plugins: {
        legend: { display: true, position: "bottom", labels: { color: "#7b9fc9", font: { size: 11 }, boxWidth: 12, padding: 10 } },
        tooltip: {
          backgroundColor: "rgba(13,30,53,0.95)", borderColor: "rgba(99,160,255,0.3)", borderWidth: 1,
          titleColor: "#e2eaf8", bodyColor: "#7b9fc9",
          callbacks: { label: ctx => ctx.dataset.yAxisID === "incident" ? (ctx.raw ? "⚠ Incident" : "✓ Clear") : `${ctx.raw} km/h` },
        },
      },
      scales: {
        speed:    { beginAtZero: false, title: { display: true, text: "km/h", color: "#7b9fc9" }, ticks: { color: "#7b9fc9", font: { size: 10 } }, grid: { color: "rgba(99,160,255,0.06)" } },
        incident: { beginAtZero: true, display: false, max: 1, min: 0 },
        x:        { ticks: { color: "#7b9fc9", font: { size: 10 }, maxRotation: 30 }, grid: { color: "rgba(99,160,255,0.06)" } },
      },
    },
  });
}

// ══════════════════════════════════════════════
// PREDICTION
// ══════════════════════════════════════════════
const CONG_GRAD   = { low: "linear-gradient(135deg,#10b981,#06b6d4)", medium: "linear-gradient(135deg,#f59e0b,#f97316)", high: "linear-gradient(135deg,#ef4444,#dc2626)" };
const CONG_BORDER = { low: "#10b981", medium: "#f59e0b", high: "#ef4444" };

function updatePrediction(data) {
  const c = data.predicted_congestion;
  predictedCongestion.textContent = c;
  predictedCongestion.style.backgroundImage = CONG_GRAD[c] || CONG_GRAD.low;
  estimatedDelay.textContent = `⏱ ${data.estimated_delay_minutes} min estimated delay`;
  predictionCard.style.borderLeftColor = CONG_BORDER[c] || "#3b82f6";
  predictionTime.textContent = `${data.location} · ${fmtTime(data.predicted_time)}`;

  const conf = Math.round((data.confidence || 0) * 100);
  if (confidenceBar) confidenceBar.style.width = `${conf}%`;
  if (confidencePct) confidencePct.textContent = `${conf}%`;

  if (c === "high") {
    alertPill.className = "status-pill alert";
    alertText.textContent = "High Congestion Alert";
  } else {
    alertPill.className = "status-pill monitoring";
    alertText.textContent = "Monitoring";
  }
}

// ══════════════════════════════════════════════
// ROUTE STEPS
// ══════════════════════════════════════════════
function renderSteps(steps) {
  if (!steps?.length) { routeSteps.classList.add("hidden"); return; }
  routeSteps.classList.remove("hidden");
  routeSteps.innerHTML = `<h4>Turn-by-turn directions</h4>` +
    steps.slice(0, 8).map((s, i) =>
      `<div class="step-item"><span class="step-num">${i+1}</span><span>${esc(s)}</span></div>`
    ).join("");
}

// ══════════════════════════════════════════════
// LOAD DASHBOARD
// ══════════════════════════════════════════════
async function loadDashboard(location = currentLocation) {
  currentLocation = location || "MG Road";
  const q = encodeURIComponent(currentLocation);

  try {
    const payload = await fetchJson(`/traffic-data?location=${q}`);
    const rows    = payload.results || payload;
    renderRows(rows);
    drawTrend(rows);
    feedStatus.textContent = `${currentLocation} · refreshed ${fmtTime(new Date())}`;
  } catch (err) { feedStatus.textContent = `⚠ ${err.message}`; }

  try {
    const pred = await fetchJson(`/predict?location=${q}&horizon_minutes=60`);
    updatePrediction(pred);
  } catch (err) {
    predictedCongestion.textContent = "Error";
    estimatedDelay.textContent = err.message;
  }

  // Reload intensity circles and peak forecast whenever location changes
  await Promise.allSettled([
    loadIntensityCircles(),
    loadPeakForecast(currentLocation),
  ]);
}

// ══════════════════════════════════════════════
// EVENT LISTENERS
// ══════════════════════════════════════════════
predictionForm.addEventListener("submit", async e => {
  e.preventDefault();
  const loc = String(new FormData(predictionForm).get("location") || "").trim();
  if (!loc) return;
  predictedCongestion.textContent = "…";
  estimatedDelay.textContent = "Refreshing…";
  await loadDashboard(loc);
});

routeForm.addEventListener("submit", async e => {
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
    const data   = await fetchJson(`/optimize-route?origin=${encodeURIComponent(org)}&destination=${encodeURIComponent(dest)}`);
    const r      = data.best_route;
    const mapped = drawRealRoute(data, org, dest);

    routeProvider.textContent = (data.provider || "geoapify").toUpperCase();
    routeResult.innerHTML = `
      <strong style="font-size:14px;color:#e2eaf8">${esc(r.summary || "Optimal Route")}</strong><br>
      <span style="color:#06b6d4;font-weight:600">🕒 ${esc(r.duration_in_traffic_text || r.duration_text || "—")}</span>
      &nbsp;·&nbsp;
      <span style="color:#7b9fc9">📍 ${esc(r.distance_text || "—")}</span>
      <br><small style="color:${mapped ? '#10b981' : '#f59e0b'};margin-top:4px;display:block">
        ${mapped ? "✓ Route drawn on map" : "⚠ No real geometry — showing estimate"}
      </small>`;
    renderSteps(r.steps);
  } catch (err) {
    routeResult.innerHTML = `<p style="color:#ef4444">⚠ ${esc(err.message)}</p>`;
    clearRoute();
  }
});

// ══════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════
document.addEventListener("DOMContentLoaded", async () => {
  initMap();

  await loadDashboard(currentLocation);

  // Auto-draw initial route for visual wow on load
  try {
    const data = await fetchJson("/optimize-route?origin=MG+Road&destination=Airport+Road");
    drawRealRoute(data, "MG Road", "Airport Road");
  } catch (_) {}

  loadingOverlay?.classList.add("hidden");
});

setInterval(() => {
  loadDashboard(currentLocation).catch(err => {
    feedStatus.textContent = `⚠ Auto-refresh failed: ${err.message}`;
  });
}, REFRESH_MS);
