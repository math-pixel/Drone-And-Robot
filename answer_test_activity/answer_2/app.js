// app.js (basé sur ton code, modifs minimales)
const WS_URL = window.APP_CONFIG.WS_URL;
const MAPPING_URL = "./answer_2.mapping.json"; // { "1": "a", "2": "b", ... }
const QCM_URL = "../../test_activity/qcm.geometry.json"; // ajuste si besoin (même fichier que test_activity)

const els = {
  btnConnect: document.getElementById("btnConnect"),
  btnStart: document.getElementById("btnStart"),

  screenConnect: document.getElementById("screenConnect"),
  screenStart: document.getElementById("screenStart"),
  screenAnswer: document.getElementById("screenAnswer"),

  btnLetter: document.getElementById("btnLetter"),
};

let ws = null;
let lastRoot = null;

let mapping = {}; // actionId -> 'a'|'b'|'c'
let correctById = new Map(); // actionId -> 'A'|'B'|'C'

let currentActionId = null;
let currentLetter = null;
let readyToClick = false;

let canStart = false;
let waitingFinishedForActionId = null;

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
  els.screenStart.classList.toggle("hidden", name !== "start");
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

async function loadQcm() {
  try {
    const res = await fetch(QCM_URL, { cache: "no-store" });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const qcm = await res.json();
    if (!qcm || !Array.isArray(qcm.questions)) throw new Error("qcm invalid");

    correctById = new Map();
    for (const q of qcm.questions) {
      correctById.set(Number(q.number), String(q.correct || "").toUpperCase());
    }
  } catch {
    correctById = new Map();
  }
}

function resetUI() {
  currentActionId = null;
  currentLetter = null;
  readyToClick = false;
  waitingFinishedForActionId = null;

  els.btnLetter.textContent = "—";
  els.btnLetter.disabled = true;
  els.btnLetter.classList.remove("good", "bad");
}

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  els.btnConnect.disabled = true;
  showScreen("start");
  els.btnStart.disabled = true;
  canStart = false;

  ws = new WebSocket(WS_URL);

  ws.onmessage = (evt) => {
    const raw = typeof evt.data === "string" ? evt.data : "";
    const parsed = safeJsonParse(raw);
    if (!parsed) return;

    const root = normalizeRoot(parsed);
    if (!root) return;

    lastRoot = root;
    const key = String(root.key || "");

    if (key === "identification_request") {
      sendIdentificationAnswer2();
      canStart = true;
      els.btnStart.disabled = false;
      return;
    }

    const mStarted = key.match(/^test_activity_step_1_action_(\d+)_started$/);
    if (mStarted) {
      onActionStarted(Number(mStarted[1]));
      return;
    }

    const mFinished = key.match(/^test_activity_step_1_action_(\d+)_finished$/);
    if (mFinished) {
      onActionFinished(Number(mFinished[1]));
      return;
    }
  };

  ws.onerror = () => {
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
  out.key = "identification_answer_2_test_activity";

  if (!Array.isArray(out.activity)) out.activity = [];

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
}

function sendStart() {
  if (!canStart) return;
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = "test_activity_start";
  ws.send(JSON.stringify(out));

  els.btnStart.disabled = true;
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

  els.btnLetter.classList.remove("good", "bad");
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

  // attente du _finished pour colorer
  readyToClick = false;
  waitingFinishedForActionId = currentActionId;

  els.btnLetter.disabled = true;
}

function onActionFinished(actionId) {
  if (
    waitingFinishedForActionId == null ||
    actionId !== waitingFinishedForActionId
  )
    return;

  const correct = (correctById.get(actionId) || "").toUpperCase(); // "A"|"B"|"C"
  const picked = (currentLetter || "").toUpperCase(); // "A"|"B"|"C"

  els.btnLetter.classList.remove("good", "bad");
  if (correct && picked) {
    els.btnLetter.classList.add(picked === correct ? "good" : "bad");
  }

  // ensuite on attend une prochaine _started
  waitingFinishedForActionId = null;
  currentActionId = null;
  currentLetter = null;
}

els.btnConnect.addEventListener("click", connect);
els.btnStart.addEventListener("click", sendStart);
els.btnLetter.addEventListener("click", sendAnswer);

loadMapping();
loadQcm();
showScreen("connect");
resetUI();
