// app.js
const WS_URL = window.APP_CONFIG.WS_URL;
const RECONNECT_MS = 5000;

// Map key -> audio file
const SOUND_BY_KEY = {
  // examples (modifie selon tes keys)
  global_sound_: "./vrai.mp3",
  // "some_key": "./sounds/some.mp3",
};

const els = {
  dot: document.getElementById("dot"),
  statusText: document.getElementById("statusText"),
  wsUrl: document.getElementById("wsUrl"),
  log: document.getElementById("log"),
  btnEnableAudio: document.getElementById("btnEnableAudio"),
};

els.wsUrl.textContent = WS_URL;

let ws = null;
let reconnectTimer = null;
let audioEnabled = false;
let lastRoot = null;

// one Audio element per file (cache)
const audioCache = new Map();

function log(line) {
  const ts = new Date().toLocaleTimeString();
  els.log.value = `[${ts}] ${line}\n` + els.log.value;
}

function setConnected(connected) {
  els.statusText.textContent = connected ? "CONNECTED" : "DISCONNECTED";
  els.dot.classList.toggle("ok", connected);
}

function safeJsonParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}
function normalizeRoot(parsed) {
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed))
    return parsed;
  if (Array.isArray(parsed) && parsed[0] && typeof parsed[0] === "object")
    return parsed[0];
  return null;
}
function structuredCloneSafe(obj) {
  if (typeof structuredClone === "function") return structuredClone(obj);
  return JSON.parse(JSON.stringify(obj));
}

function getAudio(file) {
  if (!audioCache.has(file)) {
    const a = new Audio(file);
    a.preload = "auto";
    audioCache.set(file, a);
  }
  return audioCache.get(file);
}

async function playSound(file) {
  if (!audioEnabled) {
    log(`🔇 audio disabled (blocked) — wanted: ${file}`);
    return;
  }
  try {
    const a = getAudio(file);
    a.currentTime = 0;
    await a.play();
    log(`🔊 played: ${file}`);
  } catch (e) {
    log(`🔇 play failed: ${file} (${String(e?.message || e)})`);
  }
}

function handleKey(key) {
  if (!key) return;

  const file = SOUND_BY_KEY[key];
  if (file) {
    log(`key=${key}`);
    playSound(file);
  } else {
    log(`key=${key} (unknown)`);
  }
}

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_MS);
}

function sendIdentificationSoundAtmosphere() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = "identification_sound_atmosphere_activity";

  if (!Array.isArray(out.activity)) out.activity = [];

  let found = false;
  for (const entry of out.activity) {
    console.log(entry);
    if (entry && typeof entry === "object" && entry.sound_atmosphere_activity) {
      entry.sound_atmosphere_activity.connected = true;
      found = true;
      break;
    }
  }

  if (!found) {
    out.activity.push({
      sound_atmosphere_activity: {
        ws_session_id: "",
        connected: true,
        step: [],
      },
    });
  }

  ws.send(JSON.stringify(out));
  log("↩️ sent: identification_sound_atmosphere_activity (connected=true)");
}

function connect() {
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    return;
  }

  log(`Connecting to ${WS_URL}…`);
  try {
    ws = new WebSocket(WS_URL);
  } catch (e) {
    log(`WebSocket ctor error: ${String(e?.message || e)}`);
    setConnected(false);
    scheduleReconnect();
    return;
  }

  ws.onopen = () => {
    log("WebSocket open");
    setConnected(true);
  };

  ws.onmessage = (evt) => {
    const raw = typeof evt.data === "string" ? evt.data : "";
    const parsed = safeJsonParse(raw);
    const root = parsed ? normalizeRoot(parsed) : null;
    if (!root) {
      log("message (invalid json)");
      return;
    }

    lastRoot = root;

    const key = String(root.key || "");
    switch (key) {
      case "identification_request":
        log("key=identification_request");
        sendIdentificationSoundAtmosphere();
        break;

      default:
        // ton code existant: jouer son selon SOUND_BY_KEY / log unknown
        handleKey(key);
        break;
    }
  };

  ws.onerror = () => {
    log("WebSocket error");
  };

  ws.onclose = (evt) => {
    log(`WebSocket closed (code=${evt.code})`);
    setConnected(false);
    ws = null;
    scheduleReconnect();
  };
}

// iOS/Safari: need a user gesture once
els.btnEnableAudio.addEventListener("click", async () => {
  try {
    audioEnabled = true;
    // warmup: play a silent-ish attempt by creating an Audio and calling play/pause quickly
    // (some browsers still require a real file; we just mark enabled)
    els.btnEnableAudio.disabled = true;
    els.btnEnableAudio.textContent = "Audio enabled";
    log("Audio enabled by user");
  } catch {
    audioEnabled = false;
    log("Failed to enable audio");
  }
});

// auto connect loop
setConnected(false);
connect();
scheduleReconnect(); // in case first connect fails silently
