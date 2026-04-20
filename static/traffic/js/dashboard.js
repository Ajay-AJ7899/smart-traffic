const tableBody = document.querySelector("#traffic-table");
const predictionForm = document.querySelector("#prediction-form");
const routeForm = document.querySelector("#route-form");
const predictionCard = document.querySelector("#prediction-card");
const predictedCongestion = document.querySelector("#predicted-congestion");
const estimatedDelay = document.querySelector("#estimated-delay");
const predictionTime = document.querySelector("#prediction-time");
const routeResult = document.querySelector("#route-result");
const routeProvider = document.querySelector("#route-provider");
const alertPill = document.querySelector("#alert-pill");
const mapNode = document.querySelector("#map");

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return response.json();
}

function renderRows(rows) {
  tableBody.innerHTML = rows
    .slice(0, 12)
    .map((row) => {
      const date = new Date(row.timestamp).toLocaleString();
      return `
        <tr>
          <td>${date}</td>
          <td>${row.location}</td>
          <td>${row.congestion_level}</td>
          <td>${row.avg_speed} km/h</td>
          <td>${row.incidents || "-"}</td>
        </tr>
      `;
    })
    .join("");
}

function drawTrend(rows) {
  const canvas = document.querySelector("#trend-chart");
  const labels = rows.slice(0, 12).reverse().map((row) => new Date(row.timestamp).getHours() + ":00");
  const speeds = rows.slice(0, 12).reverse().map((row) => row.avg_speed);

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Average speed",
          data: speeds,
          borderColor: "#2266cc",
          backgroundColor: "rgba(34, 102, 204, 0.12)",
          fill: true,
          tension: 0.35,
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function updatePrediction(data) {
  predictedCongestion.textContent = data.predicted_congestion;
  estimatedDelay.textContent = `${data.estimated_delay_minutes} min estimated delay`;
  predictionTime.textContent = new Date(data.predicted_time).toLocaleString();
  const colors = { low: "#169b62", medium: "#d88716", high: "#d93f3f" };
  predictionCard.style.borderLeftColor = colors[data.predicted_congestion] || "#2266cc";
  alertPill.textContent = data.predicted_congestion === "high" ? "High congestion alert" : "Monitoring";
}

async function loadDashboard() {
  const trafficPayload = await fetchJson("/traffic-data");
  const rows = trafficPayload.results || trafficPayload;
  renderRows(rows);
  drawTrend(rows);
  const prediction = await fetchJson("/predict?location=MG%20Road&horizon_minutes=60");
  updatePrediction(prediction);
}

predictionForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(predictionForm);
  const location = encodeURIComponent(form.get("location"));
  const data = await fetchJson(`/predict?location=${location}&horizon_minutes=60`);
  updatePrediction(data);
});

routeForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(routeForm);
  const origin = encodeURIComponent(form.get("origin"));
  const destination = encodeURIComponent(form.get("destination"));
  const data = await fetchJson(`/optimize-route?origin=${origin}&destination=${destination}`);
  routeProvider.textContent = data.provider;
  routeResult.innerHTML = `
    <strong>${data.best_route.summary}</strong><br>
    ${data.best_route.duration_in_traffic_text || "No live traffic"} -
    ${data.best_route.distance_text || "distance unavailable"}<br>
    <small>${data.live_traffic_available ? "Live traffic enabled" : "Configure Maps API for live optimization"}</small>
  `;
});

loadDashboard().catch((error) => {
  routeResult.textContent = error.message;
});

function initGoogleTrafficMap() {
  const map = new google.maps.Map(mapNode, {
    center: { lat: 12.9716, lng: 77.5946 },
    zoom: 12,
    disableDefaultUI: true,
    zoomControl: true,
  });
  const trafficLayer = new google.maps.TrafficLayer();
  trafficLayer.setMap(map);
}

function loadLiveMapIfConfigured() {
  const provider = mapNode.dataset.provider;
  const apiKey = mapNode.dataset.googleKey;
  if (provider !== "google" || !apiKey) {
    return;
  }
  mapNode.innerHTML = "";
  window.initGoogleTrafficMap = initGoogleTrafficMap;
  const script = document.createElement("script");
  script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&callback=initGoogleTrafficMap`;
  script.async = true;
  document.head.appendChild(script);
}

loadLiveMapIfConfigured();
