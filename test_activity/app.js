// app.js
const WS_URL = "ws://192.168.1.13:8057/ws";
const STEPS_URL = "./steps.test_activity.json";
const QCM_URL = "./qcm.geometry.json";

const els = {
  status: document.getElementById("status"),
  btnConnect: document.getElementById("btnConnect"),
  connectHint: document.getElementById("connectHint"),

  screenConnect: document.getElementById("screenConnect"),
  screenQuiz: document.getElementById("screenQuiz"),
  screenDone: document.getElementById("screenDone"),

  progress: document.getElementById("progress"),
  timer: document.getElementById("timer"),
  question: document.getElementById("question"),
  optA: document.getElementById("optA"),
  optB: document.getElementById("optB"),
  optC: document.getElementById("optC"),
  feedback: document.getElementById("feedback"),

  log: document.getElementById("log"),
  logDone: document.getElementById("logDone"),
};

let ws = null;

/** Latest received root object (server sends object OR [object]) */
let lastRoot = null;

/** Loaded step payload (array) */
let TEST_ACTIVITY_STEPS = null;

/** Loaded QCM questions + correct answers */
let QCM = null;
/** Map actionId(number) => correctLetter('A'|'B'|'C') */
let correctById = new Map();

/** Quiz runtime state */
let actions = []; // actions list (20)
let currentIndex = -1; // 0..n-1
let currentActionId = null; // number
let awaitingAnswer = false;

let countdownInterval = null;
let countdownTimeout = null;
let nextQuestionTimeout = null;

function log(line) {
  const ts = new Date().toLocaleTimeString();
  if (els.log) els.log.value = `[${ts}] ${line}\n` + els.log.value;
  if (els.logDone) els.logDone.value = `[${ts}] ${line}\n` + els.logDone.value;
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

function findActivityObj(root, activityKey) {
  const arr = root?.activity;
  if (!Array.isArray(arr)) return null;

  for (const entry of arr) {
    if (entry && typeof entry === "object" && entry[activityKey])
      return entry[activityKey];
  }
  return null;
}

function showScreen(name) {
  els.screenConnect.classList.toggle("hidden", name !== "connect");
  els.screenQuiz.classList.toggle("hidden", name !== "quiz");
  els.screenDone.classList.toggle("hidden", name !== "done");
}

async function loadJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return await res.json();
}

async function bootLoad() {
  try {
    TEST_ACTIVITY_STEPS = await loadJson(STEPS_URL);
    if (!Array.isArray(TEST_ACTIVITY_STEPS))
      throw new Error("steps JSON must be an array");

    QCM = await loadJson(QCM_URL);
    if (!QCM || !Array.isArray(QCM.questions))
      throw new Error("qcm JSON invalid");

    correctById = new Map();
    for (const q of QCM.questions) {
      correctById.set(Number(q.number), String(q.correct).toUpperCase());
    }

    // We expect: STEPS[0].actions = [...]
    const step0 = TEST_ACTIVITY_STEPS?.[0];
    actions = Array.isArray(step0?.actions) ? step0.actions : [];

    log(
      `Loaded steps (${actions.length} actions) and QCM (${QCM.questions.length} questions)`
    );
  } catch (e) {
    log(`Boot load failed: ${String(e.message || e)}`);
    els.connectHint.textContent =
      "Erreur: JSON steps/qcm introuvable ou invalide.";
  }
}

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  showScreen("connect");
  setStatus("CONNECTING…");
  log(`Connecting to ${WS_URL}`);

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    setStatus("CONNECTED", true, false);
    els.btnConnect.disabled = true;
    els.connectHint.textContent = "Connecté. Attente des données du serveur…";
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

    // 1) On identification_request -> send identification_test_activity with steps + connected
    if (key === "identification_request") {
      sendIdentificationWithSteps();
      return;
    }

    // 2) Wait for authorization key before starting quiz
    if (key === "test_activity_step_1_authorization") {
      startQuiz();
      return;
    }

    // 3) During quiz: listen for answer keys
    if (awaitingAnswer && currentActionId != null) {
      const prefix = `test_activity_step_1_action_${currentActionId}_`;
      if (key.startsWith(prefix)) {
        const suffix = key.slice(prefix.length).toLowerCase(); // 'a'|'b'|'c' or other
        if (suffix === "a" || suffix === "b" || suffix === "c") {
          onAnswerReceived(suffix);
        }
      }
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
    els.connectHint.textContent = "Déconnecté.";
    stopAllTimers();
    showScreen("connect");
  };
}

function stopAllTimers() {
  if (countdownInterval) clearInterval(countdownInterval);
  if (countdownTimeout) clearTimeout(countdownTimeout);
  if (nextQuestionTimeout) clearTimeout(nextQuestionTimeout);
  countdownInterval = null;
  countdownTimeout = null;
  nextQuestionTimeout = null;
}

function wsSendRootWithKey(newKey) {
  if (!ws || ws.readyState !== WebSocket.OPEN) return false;
  if (!lastRoot) return false;

  const out = structuredCloneSafe(lastRoot);
  out.key = newKey;
  ws.send(JSON.stringify(out));
  log(`Sent key=${newKey}`);
  return true;
}

function sendIdentificationWithSteps() {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  if (!lastRoot) return;

  const out = structuredCloneSafe(lastRoot);
  out.key = "identification_test_activity";

  const testActivity = findActivityObj(out, "test_activity");
  if (testActivity && typeof testActivity === "object") {
    testActivity.connected = true;

    if (Array.isArray(TEST_ACTIVITY_STEPS)) {
      // NOTE: you said you renamed to `steps` (plural)
      testActivity.steps = structuredCloneSafe(TEST_ACTIVITY_STEPS);
    } else {
      testActivity.steps = [];
      log("Warning: steps not loaded (test_activity.steps sent empty)");
    }
  } else {
    log("Warning: test_activity not found in payload");
  }

  ws.send(JSON.stringify(out));
  log("Sent identification_test_activity (connected=true + steps)");
  els.connectHint.textContent =
    "Identification envoyée. Attente d’autorisation…";
}

function startQuiz() {
  if (!actions.length) {
    log("No actions loaded, cannot start quiz");
    return;
  }

  showScreen("quiz");
  els.feedback.textContent = "";
  els.feedback.className = "feedback";
  currentIndex = -1;

  log("Authorization received, starting quiz");
  nextQuestion();
}

function renderQuestion(action, index, total) {
  els.progress.textContent = `Question ${index + 1}/${total}`;
  els.question.textContent = action.name || `Question ${action.id}`;

  const opts = Array.isArray(action.options) ? action.options : [];
  els.optA.textContent = opts[0]?.text ?? "—";
  els.optB.textContent = opts[1]?.text ?? "—";
  els.optC.textContent = opts[2]?.text ?? "—";

  els.feedback.textContent = "";
  els.feedback.className = "feedback";
}

function nextQuestion() {
  stopAllTimers();

  currentIndex += 1;

  if (currentIndex >= actions.length) {
    finishQuiz();
    return;
  }

  const action = actions[currentIndex];
  currentActionId = Number(action.id);
  awaitingAnswer = true;

  renderQuestion(action, currentIndex, actions.length);

  // Send "started" key using the *latest* JSON received
  wsSendRootWithKey(`test_activity_step_1_action_${currentActionId}_started`);

  // Start 8s timer
  let remaining = 8;
  els.timer.textContent = `${remaining}s`;

  countdownInterval = setInterval(() => {
    remaining -= 1;
    if (remaining < 0) remaining = 0;
    els.timer.textContent = `${remaining}s`;
  }, 1000);

  countdownTimeout = setTimeout(() => {
    // no answer received in time
    onTimeout();
  }, 8000);
}

function onTimeout() {
  if (!awaitingAnswer) return;
  awaitingAnswer = false;
  stopAllTimers();
  showFeedback(false);
  nextQuestionTimeout = setTimeout(nextQuestion, 3000);
}

function onAnswerReceived(letterLower) {
  if (!awaitingAnswer) return;
  awaitingAnswer = false;
  stopAllTimers();

  const picked = letterLower.toUpperCase(); // A/B/C
  const correct = correctById.get(currentActionId) || null;

  const isCorrect = correct ? picked === correct : false;
  showFeedback(isCorrect);

  nextQuestionTimeout = setTimeout(nextQuestion, 3000);
}

function showFeedback(ok) {
  if (ok) {
    els.feedback.textContent = "Bonne réponse ✅";
    els.feedback.className = "feedback ok";
  } else {
    els.feedback.textContent = "Mauvaise réponse ❌";
    els.feedback.className = "feedback ko";
  }
}

function finishQuiz() {
  stopAllTimers();
  awaitingAnswer = false;
  currentActionId = null;

  wsSendRootWithKey("test_activity_step_1_finished");
  log("Quiz finished, sent test_activity_step_1_finished");

  showScreen("done");
}

els.btnConnect.addEventListener("click", () => connect());

// Load JSON assets on page load
bootLoad();
