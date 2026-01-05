// app.js (minimal UX version, still robust)
const WS_URL = "ws://172.28.55.91:8057/ws";
const MAPPING_URL = "./answer_1.mapping.json"; // { "1": "a", "2": "b", ... }

const els = {
  btnConnect: document.getElementById("btnConnect"),
  screenConnect: document.getElementById("screenConnect"),
  screenAnswer: document.getElementById("screenAnswer"),
  btnLetter: document.getElementById("btnLetter"),
};

let ws = null;
let lastRoot = null;

let mapping = {}; // actionId -> 'a'|'b'|'c'
let currentActionId = null;
let currentLetter = null;
let readyToClick = false;

function safeJsonParse(str) {
  try {
    return JSON.parse(str);
  } catch {
    return null;
  }
}

function structuredCloneSafe(obj) {
  if (typeof structuredClone === "function") return structuredClone(obj);
  return JSON.parse(JSON.stringify(obj));
}

function normalizeRoot(parsed) {
  if (parsed && typeof parsed === "object" && !Array.isArray(parsed))
    return parsed;
  if (Array.isArray(parsed) && parsed[0] && typeof parsed[0] === "object")
    return parsed[0];
  return null;
}

function showScreen(name) {
  els.screenConnect.classList.toggle("hidden", name !== "connect");
  els.screenAnswer.classList.toggle("hidden", name !== "answer");
}

async function loadMapping() {
  try {
    const res = await fetch(MAPPING_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data || typeof data !== "object" || Array.isArray(data))
      throw new Error("mapping must be an object");
    mapping = data;
  } catch {
    mapping = {};
  }
}

function resetUI() {
  currentActionId = null;
  currentLetter = null;
  readyToClick = false;

  els.btnLetter.textContent = "—";
  els.btnLetter.disabled = true;
}

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  els.btnConnect.disabled = true;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    // wait for identification_request
  };

  ws.onmessage = (evt) => {
    const raw = typeof evt.data === "string" ? evt.data : "";
    const parsed = safeJsonParse(raw);
    if (!parsed) return;

    const root = normalizeRoot(parsed);
    if (!root) return;

    lastRoot = root;
    const key = String(root.key || "");

    // On identification_request -> reply identification_answer_1_test_activity (connected=true)
    if (key === "identification_request") {
      sendIdentificationAnswer2();
      return;
    }

    // Wait for started keys
    const m = key.match(/^test_activity_step_1_action_(\d+)_started$/);
    if (m) {
      onActionStarted(Number(m[1]));
      return;
    }
  };

  ws.onerror = () => {
    // allow reconnect
    els.btnConnect.disabled = false;
    ws = null;
    lastRoot = null;
    resetUI();
    showScreen("connect");
  };

  ws.onclose = () => {
    els.btnConnect.disabled = false;
    ws = null;
    lastRoot = null;
    resetUI();
    showScreen("connect");
  };
}

function sendIdentificationAnswer2() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = "identification_answer_1_test_activity";

  if (!Array.isArray(out.activity)) out.activity = [];

  let found = false;
  for (const entry of out.activity) {
    if (entry && typeof entry === "object" && entry["answer_1_test_activity"]) {
      entry["answer_1_test_activity"].connected = true;
      found = true;
      break;
    }
  }

  if (!found) {
    out.activity.push({
      answer_1_test_activity: {
        authorized: false,
        finished: false,
        ws_session_id: "",
        connected: true,
        steps: [],
      },
    });
  }

  ws.send(JSON.stringify(out));

  showScreen("answer");
  resetUI();
}

function onActionStarted(actionId) {
  const letter = String(mapping[String(actionId)] || "").toLowerCase();
  if (letter !== "a" && letter !== "b" && letter !== "c") {
    resetUI();
    showScreen("answer");
    return;
  }

  currentActionId = actionId;
  currentLetter = letter;
  readyToClick = true;

  els.btnLetter.textContent = letter.toUpperCase();
  els.btnLetter.disabled = false;

  showScreen("answer");
}

function sendAnswer() {
  if (!readyToClick) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;
  if (currentActionId == null || !currentLetter) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = `test_activity_step_1_action_${currentActionId}_${currentLetter}`;

  ws.send(JSON.stringify(out));

  // hide until next started
  resetUI();
}

els.btnConnect.addEventListener("click", () => {
  connect();
});

els.btnLetter.addEventListener("click", () => {
  sendAnswer();
});

loadMapping();
showScreen("connect");
resetUI();
