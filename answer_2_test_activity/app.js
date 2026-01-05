// app.js
const WS_URL = "ws://172.28.55.91:8057/ws";
const MAPPING_URL = "./answer_2.mapping.json"; // { "1": "a", "2": "b", ... }

const els = {
  status: document.getElementById("status"),
  btnConnect: document.getElementById("btnConnect"),
  hint: document.getElementById("hint"),
  log: document.getElementById("log"),
  log2: document.getElementById("log2"),

  screenConnect: document.getElementById("screenConnect"),
  screenAnswer: document.getElementById("screenAnswer"),

  actionLabel: document.getElementById("actionLabel"),
  btnAnswer: document.getElementById("btnAnswer"),
  answerHint: document.getElementById("answerHint"),
};

let ws = null;
let lastRoot = null;

let mapping = {}; // actionId -> 'a'|'b'|'c'
let currentActionId = null;
let currentLetter = null;
let readyToClick = false;

function log(line) {
  const ts = new Date().toLocaleTimeString();
  if (els.log) els.log.value = `[${ts}] ${line}\n` + els.log.value;
  if (els.log2) els.log2.value = `[${ts}] ${line}\n` + els.log2.value;
}

function setStatus(text, ok = false, ko = false) {
  els.status.textContent = text;
  els.status.classList.toggle("ok", ok);
  els.status.classList.toggle("ko", ko);
}

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

function findActivityObj(root, activityKey) {
  const arr = root?.activity;
  if (!Array.isArray(arr)) return null;
  for (const entry of arr) {
    if (entry && typeof entry === "object" && entry[activityKey])
      return entry[activityKey];
  }
  return null;
}

async function loadMapping() {
  try {
    const res = await fetch(MAPPING_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data || typeof data !== "object" || Array.isArray(data))
      throw new Error("mapping must be an object");
    mapping = data;
    log(`Loaded mapping (${Object.keys(mapping).length} items)`);
  } catch (e) {
    mapping = {};
    log(`Failed to load mapping: ${String(e.message || e)}`);
  }
}

function resetAnswerUI() {
  currentActionId = null;
  currentLetter = null;
  readyToClick = false;

  els.actionLabel.textContent = "Action: —";
  els.btnAnswer.textContent = "—";
  els.btnAnswer.disabled = true;
  els.answerHint.textContent = "En attente d’une action…";
}

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  setStatus("CONNECTING…");
  log(`Connecting to ${WS_URL}`);
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setStatus("CONNECTED", true, false);
    els.btnConnect.disabled = true;
    els.hint.textContent = "Connecté. Attente d’identification_request…";
    log("WebSocket open");
  };

  ws.onmessage = (evt) => {
    const raw = typeof evt.data === "string" ? evt.data : "";
    const parsed = safeJsonParse(raw);
    if (!parsed) return;

    const root = normalizeRoot(parsed);
    if (!root) return;

    lastRoot = root;
    const key = String(root.key || "");
    log(`Received key=${key}`);

    // On identification_request: reply identification_answer_1_test_activity
    if (key === "identification_request") {
      sendIdentificationAnswer1();
      return;
    }

    // Wait for started keys
    const m = key.match(/^test_activity_step_1_action_(\d+)_started$/);
    if (m) {
      const actionId = Number(m[1]);
      onActionStarted(actionId);
      return;
    }
  };

  ws.onerror = () => {
    setStatus("ERROR", false, true);
    log("WebSocket error");
  };

  ws.onclose = (evt) => {
    setStatus("DISCONNECTED");
    log(`WebSocket closed (code=${evt.code})`);
    ws = null;
    lastRoot = null;
    els.btnConnect.disabled = false;
    els.hint.textContent = "Déconnecté.";
    resetAnswerUI();
    showScreen("connect");
  };
}

function sendIdentificationAnswer1() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = "identification_answer_2_test_activity";

  // add/update answer_1_test_activity in root.activity
  // your server structure uses root.activity as array of objects
  if (!Array.isArray(out.activity)) out.activity = [];

  // find existing
  let found = false;
  for (const entry of out.activity) {
    if (entry && typeof entry === "object" && entry["answer_2_test_activity"]) {
      entry["answer_2_test_activity"].connected = true;
      found = true;
      break;
    }
  }

  if (!found) {
    out.activity.push({
      answer_2_test_activity: {
        authorized: false,
        finished: false,
        ws_session_id: "",
        connected: true,
        steps: [],
      },
    });
  }

  ws.send(JSON.stringify(out));
  log("Sent identification_answer_2_test_activity (connected=true)");
  els.hint.textContent = "Identification envoyée. Attente des actions…";

  // show answer screen now
  showScreen("answer");
  resetAnswerUI();
}

function onActionStarted(actionId) {
  const letter = String(mapping[String(actionId)] || "").toLowerCase();
  if (letter !== "a" && letter !== "b" && letter !== "c") {
    log(`No mapping for action ${actionId} (expected 'a'|'b'|'c')`);
    resetAnswerUI();
    showScreen("answer");
    return;
  }

  currentActionId = actionId;
  currentLetter = letter;
  readyToClick = true;

  els.actionLabel.textContent = `Action: ${actionId}`;
  els.btnAnswer.textContent = letter.toUpperCase();
  els.btnAnswer.disabled = false;
  els.answerHint.textContent = "Clique pour envoyer la réponse.";
  showScreen("answer");

  log(`Action started: ${actionId} -> show ${letter.toUpperCase()}`);
}

function sendAnswer() {
  if (!readyToClick) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;
  if (currentActionId == null || !currentLetter) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = `test_activity_step_1_action_${currentActionId}_${currentLetter}`;

  ws.send(JSON.stringify(out));
  log(`Sent answer key=${out.key}`);

  // After sending, hide until next started
  resetAnswerUI();
}

els.btnConnect.addEventListener("click", connect);
els.btnAnswer.addEventListener("click", sendAnswer);

loadMapping();
showScreen("connect");
