<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Pothole Rover Telemetry Dashboard</title>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <style>
    :root {
      --bg-color: #0f172a;
      --card-bg: #1e293b;
      --accent: #38bdf8;
      --danger: #ef4444;
      --success: #22c55e;
      --text: #f8fafc;
    }
    body {
      margin: 0;
      padding: 16px;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg-color);
      color: var(--text);
    }
    header {
      display: flex;
      flex-wrap: wrap;
      justify-content: space-between;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      padding-bottom: 10px;
      border-bottom: 1px solid #334155;
    }
    h1 {
      margin: 0;
      font-size: 1.3rem;
      color: var(--accent);
    }
    .status-badge {
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.85rem;
      font-weight: bold;
    }
    .disconnected { background: #475569; }
    .connected { background: var(--success); color: #000; }
    .grid {
      display: grid;
      grid-template-columns: 1fr;
      gap: 16px;
    }
    @media (min-width: 850px) {
      .grid { grid-template-columns: 1fr 1fr; }
    }
    .card {
      background: var(--card-bg);
      border-radius: 12px;
      padding: 16px;
      box-shadow: 0 4px 6px -1px rgba(0,0,0,0.4);
    }
    .card h2 {
      margin-top: 0;
      font-size: 1.1rem;
      color: #94a3b8;
    }
    video {
      width: 100%;
      height: 240px;
      object-fit: cover;
      border-radius: 8px;
      background: #000;
    }
    #map {
      width: 100%;
      height: 240px;
      border-radius: 8px;
      background: #334155;
    }
    .controls {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 8px;
      margin-top: 10px;
    }
    .control-row {
      display: flex;
      gap: 8px;
    }
    button {
      background: #334155;
      color: white;
      border: none;
      padding: 10px 16px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
      transition: background 0.15s ease;
    }
    button:hover { background: #475569; }
    button:active { background: var(--accent); color: black; }
    button.danger { background: var(--danger); }
    .telemetry-row {
      display: flex;
      justify-content: space-between;
      padding: 6px 0;
      border-bottom: 1px solid #334155;
      font-size: 0.95rem;
    }
    .ip-input {
      background: #0f172a;
      border: 1px solid #475569;
      color: #fff;
      padding: 6px 10px;
      border-radius: 6px;
      font-size: 0.9rem;
    }
  </style>
</head>
<body>

  <header>
    <h1>🚗 Pothole Rover Telemetry</h1>
    <div>
      <input type="text" id="espIp" class="ip-input" value="192.168.4.1" placeholder="ESP32 IP">
      <button id="wsBtn" onclick="toggleWebSocket()">Connect ESP32</button>
      <span id="wsStatus" class="status-badge disconnected">Offline</span>
    </div>
  </header>

  <div class="grid">
    <!-- Camera Section -->
    <div class="card">
      <h2>Webcam View</h2>
      <video id="webcam" autoplay playsinline muted></video>
      <div style="margin-top: 10px; display: flex; gap: 8px;">
        <button onclick="startCamera()">Start Camera</button>
        <button onclick="switchCamera()">Flip Camera</button>
        <button class="danger" onclick="reportPothole()">Mark Pothole</button>
      </div>
    </div>

    <!-- Map & GPS Section -->
    <div class="card">
      <h2>Live GPS Map</h2>
      <div id="map"></div>
      <div style="margin-top: 10px;">
        <div class="telemetry-row">
          <span>Latitude:</span> <strong id="latVal">Waiting...</strong>
        </div>
        <div class="telemetry-row">
          <span>Longitude:</span> <strong id="lngVal">Waiting...</strong>
        </div>
        <div class="telemetry-row">
          <span>Ultrasonic Sensor:</span> <strong id="obstacleVal">Clear</strong>
        </div>
      </div>
    </div>

    <!-- Rover Control Buttons -->
    <div class="card" style="grid-column: 1 / -1;">
      <h2>Manual Controls</h2>
      <div class="controls">
        <button onclick="sendCommand('FORWARD')">▲ FORWARD</button>
        <div class="control-row">
          <button onclick="sendCommand('LEFT')">◄ LEFT</button>
          <button class="danger" onclick="sendCommand('STOP')">■ STOP</button>
          <button onclick="sendCommand('RIGHT')">RIGHT ►</button>
        </div>
        <button onclick="sendCommand('BACKWARD')">▼ BACKWARD</button>
      </div>
    </div>
  </div>

  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    let ws;
    let map, marker;
    let currentStream = null;
    let facingMode = "environment";
    let curLat = 16.5062, curLng = 80.6480; // Default center fallback

    // Initialize Map
    function initMap() {
      map = L.map('map').setView([curLat, curLng], 15);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19
      }).addTo(map);
      marker = L.marker([curLat, curLng]).addTo(map).bindPopup("Rover Position");
    }
    initMap();

    // Webcam Controls
    async function startCamera() {
      if (currentStream) {
        currentStream.getTracks().forEach(track => track.stop());
      }
      try {
        currentStream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: facingMode }
        });
        document.getElementById('webcam').srcObject = currentStream;
      } catch (err) {
        alert("Camera access denied or unavailable: " + err.message);
      }
    }

    function switchCamera() {
      facingMode = facingMode === "user" ? "environment" : "user";
      startCamera();
    }

    // WebSocket Connection
    function toggleWebSocket() {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.close();
        return;
      }
      const ip = document.getElementById('espIp').value.trim();
      ws = new WebSocket(`ws://${ip}:81/`);

      ws.onopen = () => {
        document.getElementById('wsStatus').textContent = "Online";
        document.getElementById('wsStatus').className = "status-badge connected";
        document.getElementById('wsBtn').textContent = "Disconnect";
      };

      ws.onmessage = (event) => {
        // Expected message formats:
        // GPS:16.506174,80.648015
        // OBSTACLE:FRONT_DETECTED or OBSTACLE:CLEAR
        const msg = event.data;
        if (msg.startsWith("GPS:")) {
          const parts = msg.replace("GPS:", "").split(",");
          const lat = parseFloat(parts[0]);
          const lng = parseFloat(parts[1]);
          if (!isNaN(lat) && !isNaN(lng)) {
            curLat = lat;
            curLng = lng;
            document.getElementById('latVal').textContent = lat.toFixed(6);
            document.getElementById('lngVal').textContent = lng.toFixed(6);
            marker.setLatLng([lat, lng]);
            map.panTo([lat, lng]);
          }
        } else if (msg.startsWith("OBSTACLE:")) {
          const status = msg.replace("OBSTACLE:", "");
          const el = document.getElementById('obstacleVal');
          el.textContent = status;
          el.style.color = (status === "FRONT_DETECTED") ? "#ef4444" : "#22c55e";
        }
      };

      ws.onclose = () => {
        document.getElementById('wsStatus').textContent = "Offline";
        document.getElementById('wsStatus').className = "status-badge disconnected";
        document.getElementById('wsBtn').textContent = "Connect ESP32";
      };

      ws.onerror = (err) => {
        console.error("WS Error:", err);
      };
    }

    function sendCommand(cmd) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(cmd);
      } else {
        console.warn("WebSocket not connected. Command dropped:", cmd);
      }
    }

    function reportPothole() {
      if (map) {
        const potholeIcon = L.circleMarker([curLat, curLng], {
          color: 'red',
          fillColor: '#f03',
          fillOpacity: 0.7,
          radius: 8
        }).addTo(map);
        potholeIcon.bindPopup(`<b>Pothole Reported!</b><br>Lat: ${curLat}<br>Lng: ${curLng}`).openPopup();
      }
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send("POTHOLE_LOGGED");
      }
    }
  </script>
</body>
</html>
