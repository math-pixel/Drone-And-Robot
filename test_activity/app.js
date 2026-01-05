// app.js (même fonctionnement, juste adapté au nouveau DOM)
const WS_URL = window.APP_CONFIG.WS_URL;
const STEPS_URL = "./steps.test_activity.json";
const QCM_URL = "./qcm.geometry.json";

const els = {
  btnConnect: document.getElementById("btnConnect"),

  screenConnect: document.getElementById("screenConnect"),
  screenWait: document.getElementById("screenWait"),
  screenQuiz: document.getElementById("screenQuiz"),
  screenDone: document.getElementById("screenDone"),

  progress: document.getElementById("progress"),
  timer: document.getElementById("timer"),
  question: document.getElementById("question"),
  optA: document.getElementById("optA"),
  optB: document.getElementById("optB"),
  optC: document.getElementById("optC"),
  feedback: document.getElementById("feedback"),
};

let ws = null;
let lastRoot = null;

let TEST_ACTIVITY_STEPS = null;
let QCM = null;
let correctById = new Map();

let actions = [];
let currentIndex = -1;
let currentActionId = null;
let awaitingAnswer = false;

let countdownInterval = null;
let countdownTimeout = null;
let nextQuestionTimeout = null;

let lastReceivedLetter = null;

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
  els.screenWait.classList.toggle("hidden", name !== "wait");
  els.screenQuiz.classList.toggle("hidden", name !== "quiz");
  els.screenDone.classList.toggle("hidden", name !== "done");
}
async function loadJson(url) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status} for ${url}`);
  return await res.json();
}
async function bootLoad() {
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

  const step0 = TEST_ACTIVITY_STEPS?.[0];
  actions = Array.isArray(step0?.actions) ? step0.actions : [];
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
    testActivity.steps = Array.isArray(TEST_ACTIVITY_STEPS)
      ? structuredCloneSafe(TEST_ACTIVITY_STEPS)
      : [];
  }

  ws.send(JSON.stringify(out));
}

function renderQuestion(action, index, total) {
  if (els.progress) els.progress.textContent = `Question ${index + 1}/${total}`;
  lastReceivedLetter = null;  
  els.question.textContent = action.name || `Question ${action.id}`;

  const opts = Array.isArray(action.options) ? action.options : [];
  els.optA.textContent = opts[0]?.text ?? "—";
  els.optB.textContent = opts[1]?.text ?? "—";
  els.optC.textContent = opts[2]?.text ?? "—";

  document
    .querySelectorAll(".hl")
    .forEach((el) => el.classList.remove("ok", "ko"));


  els.feedback.textContent = "";
  els.feedback.classList.remove("show");
}

function showFeedback(ok) {
  // reset
  document
    .querySelectorAll(".hl")
    .forEach((el) => el.classList.remove("ok", "ko"));

  const correct = (correctById.get(currentActionId) || "").toUpperCase(); // "A"|"B"|"C"

  // Correct en vert
  if (correct === "A")
    document.querySelector(".answerA .hl")?.classList.add("ok");
  if (correct === "B")
    document.querySelector(".answerB .hl")?.classList.add("ok");
  if (correct === "C")
    document.querySelector(".answerC .hl")?.classList.add("ok");

  // Les 2 autres en rouge (même si bonne réponse)
  if (correct !== "A")
    document.querySelector(".answerA .hl")?.classList.add("ko");
  if (correct !== "B")
    document.querySelector(".answerB .hl")?.classList.add("ko");
  if (correct !== "C")
    document.querySelector(".answerC .hl")?.classList.add("ko");
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

  wsSendRootWithKey(`test_activity_step_1_action_${currentActionId}_started`);

  let remaining = 8;
  els.timer.textContent = `${remaining}s`;

  countdownInterval = setInterval(() => {
    remaining -= 1;
    if (remaining < 0) remaining = 0;
    els.timer.textContent = `${remaining}s`;
  }, 1000);

  countdownTimeout = setTimeout(() => {
    if (!awaitingAnswer) return;
    awaitingAnswer = false;
    stopAllTimers();
    lastReceivedLetter = null;
    showFeedback(false);
    nextQuestionTimeout = setTimeout(nextQuestion, 3000);
  }, 8000);
}

function onAnswerReceived(letterLower) {
  if (!awaitingAnswer) return;
  awaitingAnswer = false;
  stopAllTimers();

  const picked = letterLower.toUpperCase();
  const correct = correctById.get(currentActionId) || null;
  const isCorrect = correct ? picked === correct : false;

  showFeedback(isCorrect);
  lastReceivedLetter = letterLower.toUpperCase();
  showFeedback(isCorrect);
  nextQuestionTimeout = setTimeout(nextQuestion, 3000);
}

function startQuiz() {
  if (!actions.length) return;
  currentIndex = -1;
  showScreen("quiz");
  nextQuestion();
}

function finishQuiz() {
  stopAllTimers();
  awaitingAnswer = false;
  currentActionId = null;

  wsSendRootWithKey("test_activity_step_1_finished");
  showScreen("done");
}

function connect() {
  if (
    ws &&
    (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
  )
    return;

  els.btnConnect.disabled = true;
  showScreen("wait");

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
      sendIdentificationWithSteps();
      return;
    }

    if (key === "test_activity_step_1_authorization") {
      startQuiz();
      return;
    }

    if (awaitingAnswer && currentActionId != null) {
      const prefix = `test_activity_step_1_action_${currentActionId}_`;
      if (key.startsWith(prefix)) {
        const suffix = key.slice(prefix.length).toLowerCase();
        if (suffix === "a" || suffix === "b" || suffix === "c")
          onAnswerReceived(suffix);
      }
    }
  };

  ws.onerror = () => {
    ws = null;
    lastRoot = null;
    els.btnConnect.disabled = false;
    stopAllTimers();
    showScreen("connect");
  };

  ws.onclose = () => {
    ws = null;
    lastRoot = null;
    els.btnConnect.disabled = false;
    stopAllTimers();
    showScreen("connect");
  };
}

els.btnConnect.addEventListener("click", () => connect());

bootLoad().catch(() => {
  // si JSON pas dispo, on laisse connect possible, mais ça ne jouera pas
});
showScreen("connect");
