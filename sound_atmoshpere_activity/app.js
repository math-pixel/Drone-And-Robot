// app.js
const WS_URL = window.APP_CONFIG.WS_URL;
const RECONNECT_MS = 5000;

const SOUND_PATH = "../audios/";
const SOUND_EXT = ".mp3";

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
let audioEnabled = true;
let lastRoot = null;

// one Audio element per file (cache)
const audioCache = new Map();

// loop controllers by sound name
const loopControllers = new Map(); // name -> { stop: boolean }

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

function stopLoop(name) {
  const ctrl = loopControllers.get(name);
  if (ctrl) ctrl.stop = true;
  loopControllers.delete(name);

  const file = `${SOUND_PATH}${name}${SOUND_EXT}`;
  const a = audioCache.get(file);
  if (a) {
    try {
      a.pause();
      a.currentTime = 0;
    } catch {}
  }

  log(`⏹️ loop stopped: ${name}`);
}

async function startLoop(name) {
  if (!name) return;

  // stop previous loop for same sound, then restart
  stopLoop(name);

  const ctrl = { stop: false };
  loopControllers.set(name, ctrl);

  const file = `${SOUND_PATH}${name}${SOUND_EXT}`;
  const a = getAudio(file);

  log(`🔁 loop start: ${name} -> ${file}`);

  while (!ctrl.stop) {
    if (!audioEnabled) {
      log(`🔇 audio disabled (blocked) — loop paused: ${file}`);
      break;
    }

    try {
      a.loop = false; // we handle looping ourselves
      a.currentTime = 0;
      await a.play();

      await new Promise((resolve) => {
        const onEnded = () => {
          a.removeEventListener("ended", onEnded);
          resolve();
        };
        a.addEventListener("ended", onEnded, { once: true });
      });

      log(`🔁 loop replay: ${file}`);
    } catch (e) {
      log(`🔇 loop play failed: ${file} (${String(e?.message || e)})`);
      break;
    }
  }
}

function handleKey(key) {
  if (!key) return;

  const loopPrefix = "global_sound_loop_";
  const endLoopPrefix = "global_sound_end_loop_";
  const prefix = "global_sound_";

  if (key.startsWith(loopPrefix)) {
    const name = key.slice(loopPrefix.length).trim();
    if (!name) return log(`key=${key} (invalid)`);
    startLoop(name);
    return;
  }

  if (key.startsWith(endLoopPrefix)) {
    const name = key.slice(endLoopPrefix.length).trim();
    if (!name) return log(`key=${key} (invalid)`);
    stopLoop(name);
    return;
  }

  if (!key.startsWith(prefix)) {
    log(`key=${key} (unknown)`);
    return;
  }

  const name = key.slice(prefix.length).trim();
  if (!name) {
    log(`key=${key} (invalid)`);
    return;
  }

  const file = `${SOUND_PATH}${name}${SOUND_EXT}`;
  log(`key=${key} -> ${file}`);
  playSound(file);
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
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  ) {
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

// auto connect loop
setConnected(false);
connect();
scheduleReconnect(); // in case first connect fails silently
