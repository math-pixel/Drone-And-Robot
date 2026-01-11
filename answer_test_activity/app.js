// app.js (basé sur ton code, modifs minimales)
const WS_URL = window.APP_CONFIG.WS_URL;
const MAPPING_URL = "./answer.mapping.json";
const QCM_URL = "../test_activity/qcm.geometry.json"; // ajuste si besoin (même fichier que test_activity)

const RECONNECT_MS = 5000;
let reconnectTimer = null;

function scheduleReconnect() {
  if (reconnectTimer) return;
  reconnectTimer = setTimeout(() => {
    reconnectTimer = null;
    connect();
  }, RECONNECT_MS);
}

const els = {
  btnConnect: document.getElementById("btnConnect"),
  btnStart: document.getElementById("btnStart"),

  screenConnect: document.getElementById("screenConnect"),
  screenStart: document.getElementById("screenStart"),
  screenAnswer: document.getElementById("screenAnswer"),

  btnLetter: document.getElementById("btnLetter"),
  screenPick: document.getElementById("screenPick"),
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

let pickedPlayer = null; // 1|2|3

function activityKey() {
  return pickedPlayer
    ? `answer_${pickedPlayer}_test_activity`
    : "answer_2_test_activity";
}
function identificationKey() {
  return pickedPlayer
    ? `identification_answer_${pickedPlayer}_test_activity`
    : "identification_answer_2_test_activity";
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
  els.screenPick.classList.toggle("hidden", name !== "pick");
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

    // data = { "1": {...}, "2": {...}, "3": {...} }
    if (!pickedPlayer) throw new Error("no player picked");
    const m = data[String(pickedPlayer)];
    if (!m || typeof m !== "object" || Array.isArray(m))
      throw new Error("missing mapping for picked player");

    mapping = m;
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

// ✅ REMPLACE ta fonction connect() par celle-ci
function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  // reset UI côté réseau
  canStart = false;
  els.btnStart.disabled = true;

  // si tu veux garder le bouton CONNECT utilisable après un drop, ne le lock pas définitivement
  els.btnConnect.disabled = true;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    // connecté -> on attend identification_request
  };

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
      showScreen("start");
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

    const mEcho = key.match(/^test_activity_step_1_action_(\d+)_(a|b|c)$/);
    if (mEcho) {
      onAnswerEcho(Number(mEcho[1]));
      return;
    }
  };

  ws.onerror = () => {
    // on laisse onclose gérer la reconnexion
  };

  ws.onclose = () => {
    ws = null;
    lastRoot = null;

    // UI: retour écran connect + bouton réactivé
    els.btnConnect.disabled = false;
    els.btnStart.disabled = true;
    canStart = false;

    resetUI();
    showScreen("connect");

    scheduleReconnect();
  };
}

function sendIdentificationAnswer2() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = identificationKey();

  if (!Array.isArray(out.activity)) out.activity = [];

  const aKey = activityKey();
  let found = false;
  for (const entry of out.activity) {
    if (entry && typeof entry === "object" && entry[aKey]) {
      entry[aKey].connected = true;
      found = true;
      break;
    }
  }

  if (!found) {
    out.activity.push({
      [aKey]: {
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
  els.btnLetter.classList.remove("good", "bad");

  // ✅ AJOUTE ÇA
  waitingFinishedForActionId = actionId;

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

function onAnswerEcho(actionId) {
  // on ne colore que si on est sur cette question
  if (currentActionId == null || actionId !== currentActionId) return;

  // calcule correct vs mapping pour cet actionId
  const mapped = String(mapping[String(actionId)] || "").toUpperCase(); // "A"|"B"|"C"
  const correct = String(correctById.get(actionId) || "").toUpperCase(); // "A"|"B"|"C"

  els.btnLetter.classList.remove("good", "bad");
  els.btnLetter.classList.add(
    mapped && correct && mapped === correct ? "good" : "bad"
  );

  // reste affiché/couleur jusqu’au prochain _started
  els.btnLetter.disabled = true;
}

function onActionFinished(actionId) {
  if (
    waitingFinishedForActionId == null ||
    actionId !== waitingFinishedForActionId
  )
    return;

  els.btnLetter.classList.remove("good", "bad");
  els.btnLetter.classList.add("bad");

  // ensuite on attend une prochaine _started
  waitingFinishedForActionId = null;
  currentActionId = null;
  currentLetter = null;
}

function onTap(e) {
  e.preventDefault(); // évite les doubles events / délai
  sendAnswer();
}

els.btnConnect.addEventListener("click", connect);
els.btnStart.addEventListener("click", sendStart);
els.btnLetter.addEventListener("touchstart", onTap, { passive: false });
els.btnLetter.addEventListener("click", () => sendAnswer());

loadMapping();
document.querySelectorAll(".btnPick").forEach((btn) => {
  btn.addEventListener("click", async () => {
    pickedPlayer = Number(btn.dataset.pick) || null;
    await loadMapping(); // recharge mapping avec le bon profil
    showScreen("connect");
  });
});
loadQcm();
showScreen("pick");
scheduleReconnect();
resetUI();
