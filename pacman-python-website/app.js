const codeEditor = document.getElementById("codeEditor");
const codeLineNumbers = document.getElementById("codeLineNumbers");
const codeHighlight = document.getElementById("codeHighlight");
const canvas = document.getElementById("gameCanvas");
const ctx = canvas.getContext("2d");
const consoleEl = document.getElementById("console");
const runtimeStatus = document.getElementById("runtimeStatus");
const statsEl = document.getElementById("stats");
const statePreview = document.getElementById("statePreview");
const loadCodeBtn = document.getElementById("loadCodeBtn");
const stepBtn = document.getElementById("stepBtn");
const runBtn = document.getElementById("runBtn");
const resetBtn = document.getElementById("resetBtn");
const testsBtn = document.getElementById("testsBtn");
const clearConsoleBtn = document.getElementById("clearConsoleBtn");
const levelSelect = document.getElementById("levelSelect");

const CELL_SIZE = 32;
const DECISION_TIMEOUT_MS = 900;
const RUN_DELAY_MS = 115;

const ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "STOP"];
const DIRS = {
  UP: { x: 0, y: -1 },
  DOWN: { x: 0, y: 1 },
  LEFT: { x: -1, y: 0 },
  RIGHT: { x: 1, y: 0 },
  STOP: { x: 0, y: 0 },
};

const LEVELS = {
  classic: [
    "#####################",
    "#P....#.......#....G#",
    "#.###.#.#####.#.###.#",
    "#.....#...#...#.....#",
    "###.#####.#.#####.###",
    "#.......#.#.#.......#",
    "#.#####.#.#.#.#####.#",
    "#...G...#...#...G...#",
    "#####################",
  ],
  corridors: [
    "#####################",
    "#P....#.......#.....#",
    "#.###.#.#####.#.###.#",
    "#.#...#...G...#...#.#",
    "#.#.#####.#.#####.#.#",
    "#.#.......#.......#.#",
    "#.#.#####.#.#####.#.#",
    "#...G...........G...#",
    "#####################",
  ],
  arena: [
    "#####################",
    "#P........#........G#",
    "#.###.###.#.###.###.#",
    "#.....#.......#.....#",
    "###.#.#.#####.#.#.###",
    "#...#.....G.....#...#",
    "#.###.###.#.###.###.#",
    "#G........#.........#",
    "#####################",
  ],
};

const STARTER_CODE = `# Pacman Logic Lab
# Your job: implement choose_action(state).
# The website calls this function once per game tick.

# Useful data:
# state.pacman          -> (x, y)
# state.food            -> list of (x, y)
# state.ghosts          -> list of (x, y)
# state.walls           -> set of (x, y)
# state.legal_actions   -> list like ["UP", "LEFT", "RIGHT", "STOP"]
# state.score, state.lives, state.steps
#
# Useful helpers:
# manhattan_distance(a, b)
# state.next_position(pos, action)
# state.is_wall(pos)
# state.legal_neighbors(pos)


def choose_action(state):
    """
    Return one of: "UP", "DOWN", "LEFT", "RIGHT", "STOP".
    This starter strategy chases nearby food while avoiding ghosts.
    """
    best_action = "STOP"
    best_score = -10**9

    for action in state.legal_actions:
        next_pos = state.next_position(state.pacman, action)
        score = 0

        # Prefer actions that move onto food or closer to food.
        if state.food:
            nearest_food_distance = min(
                manhattan_distance(next_pos, food)
                for food in state.food
            )
            score -= nearest_food_distance * 2

            if next_pos in state.food:
                score += 25

        # Avoid ghosts. Bigger penalty when a ghost is close.
        for ghost in state.ghosts:
            ghost_distance = manhattan_distance(next_pos, ghost)
            if ghost_distance == 0:
                score -= 1000
            elif ghost_distance == 1:
                score -= 120
            elif ghost_distance == 2:
                score -= 35
            else:
                score += min(ghost_distance, 5)

        if action == "STOP":
            score -= 5

        if score > best_score:
            best_score = score
            best_action = action

    return best_action
`;

let worker = null;
let workerReady = false;
let codeLoaded = false;
let lastLoadedCode = "";
let requestId = 0;
let pendingRequests = new Map();
let game = null;
let running = false;
let lastAction = "STOP";
let renderRequested = false;

codeEditor.value = STARTER_CODE;

function log(message, className = "") {
  const time = new Date().toLocaleTimeString();
  const line = document.createElement("span");
  if (className) {
    line.className = className;
  }
  line.textContent = `[${time}] ${message}\n`;
  consoleEl.appendChild(line);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

const EDITOR_INDENT = "    ";
const PYTHON_KEYWORDS = new Set([
  "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
]);
const PYTHON_BUILTINS = new Set([
  "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "print", "range", "round", "set", "str", "sum", "tuple", "manhattan_distance", "nearest_food",
]);

function updateEditorDecorations() {
  updateLineNumbers();
  updateSyntaxHighlight();
  syncEditorScroll();
}

function updateLineNumbers() {
  const lineCount = Math.max(1, codeEditor.value.split("\n").length);
  let numbers = "";
  for (let line = 1; line <= lineCount; line += 1) numbers += line + "\n";
  codeLineNumbers.textContent = numbers;
}

function updateSyntaxHighlight() {
  const html = highlightPython(codeEditor.value);
  codeHighlight.innerHTML = html.endsWith("\n") ? html + " " : html || " ";
}

function syncEditorScroll() {
  codeLineNumbers.scrollTop = codeEditor.scrollTop;
  codeHighlight.scrollTop = codeEditor.scrollTop;
  codeHighlight.scrollLeft = codeEditor.scrollLeft;
}

function handleEditorCommand(event) {
  if (event.key === "Tab") {
    event.preventDefault();
    if (event.shiftKey) unindentSelection();
    else indentSelection();
    return true;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    insertAutoIndent();
    return true;
  }
  if (event.key === "Backspace" && codeEditor.selectionStart === codeEditor.selectionEnd && shouldSmartOutdent()) {
    event.preventDefault();
    const cursor = codeEditor.selectionStart;
    replaceEditorRange(cursor - EDITOR_INDENT.length, cursor, "", cursor - EDITOR_INDENT.length, cursor - EDITOR_INDENT.length);
    return true;
  }
  return false;
}

function indentSelection() {
  const start = codeEditor.selectionStart;
  const end = codeEditor.selectionEnd;
  if (start === end) {
    replaceEditorRange(start, end, EDITOR_INDENT, start + EDITOR_INDENT.length, start + EDITOR_INDENT.length);
    return;
  }
  const value = codeEditor.value;
  const blockStart = value.lastIndexOf("\n", start - 1) + 1;
  const blockEnd = lineEndForSelection(value, end);
  const lines = value.slice(blockStart, blockEnd).split("\n");
  const replacement = lines.map((line) => EDITOR_INDENT + line).join("\n");
  replaceEditorRange(
    blockStart,
    blockEnd,
    replacement,
    start + EDITOR_INDENT.length,
    end + EDITOR_INDENT.length * lines.length,
  );
}

function unindentSelection() {
  const value = codeEditor.value;
  const start = codeEditor.selectionStart;
  const end = codeEditor.selectionEnd;
  const blockStart = value.lastIndexOf("\n", start - 1) + 1;
  const blockEnd = lineEndForSelection(value, end);
  const lines = value.slice(blockStart, blockEnd).split("\n");
  let removedBeforeStart = 0;
  let removedTotal = 0;
  let cursor = blockStart;
  const replacement = lines.map((line) => {
    let remove = 0;
    if (line.startsWith(EDITOR_INDENT)) remove = EDITOR_INDENT.length;
    else if (line.startsWith("\t")) remove = 1;
    if (cursor + remove <= start) removedBeforeStart += remove;
    if (cursor < end) removedTotal += remove;
    cursor += line.length + 1;
    return line.slice(remove);
  }).join("\n");
  const nextStart = Math.max(blockStart, start - removedBeforeStart);
  const nextEnd = Math.max(nextStart, end - removedTotal);
  replaceEditorRange(blockStart, blockEnd, replacement, nextStart, nextEnd);
}

function insertAutoIndent() {
  const cursor = codeEditor.selectionStart;
  const value = codeEditor.value;
  const lineStart = value.lastIndexOf("\n", cursor - 1) + 1;
  const beforeCursor = value.slice(lineStart, cursor);
  const baseIndent = beforeCursor.match(/^ */)?.[0] || "";
  const extraIndent = beforeCursor.trimEnd().endsWith(":") ? EDITOR_INDENT : "";
  const insertion = "\n" + baseIndent + extraIndent;
  replaceEditorRange(codeEditor.selectionStart, codeEditor.selectionEnd, insertion, cursor + insertion.length, cursor + insertion.length);
}

function shouldSmartOutdent() {
  const cursor = codeEditor.selectionStart;
  if (cursor < EDITOR_INDENT.length) return false;
  const lineStart = codeEditor.value.lastIndexOf("\n", cursor - 1) + 1;
  const leading = codeEditor.value.slice(lineStart, cursor);
  return leading.trim() === "" && codeEditor.value.slice(cursor - EDITOR_INDENT.length, cursor) === EDITOR_INDENT;
}

function lineEndForSelection(value, end) {
  if (end > 0 && value[end - 1] === "\n") return end - 1;
  const nextNewline = value.indexOf("\n", end);
  return nextNewline === -1 ? value.length : nextNewline;
}

function replaceEditorRange(start, end, text, nextStart, nextEnd) {
  codeEditor.setRangeText(text, start, end, "preserve");
  codeEditor.selectionStart = nextStart;
  codeEditor.selectionEnd = nextEnd;
  codeEditor.dispatchEvent(new Event("input", { bubbles: true }));
}

function blockEditorClipboard(event) {
  event.preventDefault();
  log("Copy and paste are disabled in the Pacman editor.", "warn");
}

function highlightPython(source) {
  let out = "";
  let index = 0;
  while (index < source.length) {
    const ch = source[index];
    const next = source[index + 1] || "";
    const rest = source.slice(index);
    if (ch === "#") {
      const end = source.indexOf("\n", index);
      const token = end === -1 ? source.slice(index) : source.slice(index, end);
      out += span("comment", token);
      index += token.length;
    } else if ((ch === "'" || ch === '"') && source.slice(index, index + 3) === ch.repeat(3)) {
      const token = readTripleQuoted(source, index, ch);
      out += span("string", token);
      index += token.length;
    } else if (ch === "'" || ch === '"') {
      const token = readQuoted(source, index, ch);
      out += span("string", token);
      index += token.length;
    } else if (/[0-9]/.test(ch)) {
      const match = rest.match(/^\d+(?:\.\d+)?/)[0];
      out += span("number", match);
      index += match.length;
    } else if (/[A-Za-z_]/.test(ch)) {
      const match = rest.match(/^[A-Za-z_]\w*/)[0];
      if (PYTHON_KEYWORDS.has(match)) out += span("keyword", match);
      else if (PYTHON_BUILTINS.has(match)) out += span("builtin", match);
      else out += escapeHtml(match);
      index += match.length;
    } else if (ch === "@" && /[A-Za-z_]/.test(next)) {
      const match = rest.match(/^@[A-Za-z_]\w*/)[0];
      out += span("decorator", match);
      index += match.length;
    } else if (/[+\-*\/%=<>!&|^~:.,()[\]{}]/.test(ch)) {
      out += span("operator", ch);
      index += 1;
    } else {
      out += escapeHtml(ch);
      index += 1;
    }
  }
  return out;
}

function readQuoted(source, start, quote) {
  let index = start + 1;
  while (index < source.length) {
    if (source[index] === "\\") index += 2;
    else if (source[index] === quote) return source.slice(start, index + 1);
    else index += 1;
  }
  return source.slice(start);
}

function readTripleQuoted(source, start, quote) {
  const marker = quote.repeat(3);
  const end = source.indexOf(marker, start + 3);
  return end === -1 ? source.slice(start) : source.slice(start, end + 3);
}

function span(kind, value) {
  return `<span class="tok-${kind}">${escapeHtml(value)}</span>`;
}

function setRuntimeStatus(text, mode = "loading") {
  runtimeStatus.textContent = text;
  runtimeStatus.classList.remove("status-loading", "status-ready", "status-error");
  runtimeStatus.classList.add(`status-${mode}`);
}

function setButtonsEnabled() {
  loadCodeBtn.disabled = !workerReady;
  stepBtn.disabled = !workerReady || running;
  runBtn.disabled = !workerReady;
  testsBtn.disabled = !workerReady || running;
  runBtn.textContent = running ? "Pause" : "Run";
}

function createPythonWorker() {
  if (worker) {
    worker.terminate();
  }

  workerReady = false;
  codeLoaded = false;
  pendingRequests.forEach(({ reject, timer }) => {
    clearTimeout(timer);
    reject(new Error("Python worker restarted."));
  });
  pendingRequests.clear();

  setRuntimeStatus("Loading Pyodide…", "loading");
  setButtonsEnabled();

  worker = new Worker("pyodide-worker.js");

  worker.onmessage = (event) => {
    const message = event.data || {};

    if (message.type === "ready") {
      workerReady = true;
      setRuntimeStatus(`Pyodide ${message.pyodideVersion} ready`, "ready");
      setButtonsEnabled();
      log(`Python runtime ready. Click “Load code”, then “Step once” or “Run”.`, "good");
      return;
    }

    if (message.type === "fatal") {
      workerReady = false;
      setRuntimeStatus("Pyodide failed", "error");
      log(`Fatal worker error: ${message.error}`, "bad");
      setButtonsEnabled();
      return;
    }

    if (message.id && pendingRequests.has(message.id)) {
      const pending = pendingRequests.get(message.id);
      pendingRequests.delete(message.id);
      clearTimeout(pending.timer);

      if (message.ok === false || message.type === "error") {
        pending.reject(new Error(message.error || "Python worker error."));
      } else {
        pending.resolve(message);
      }
      return;
    }

    if (message.type === "error") {
      log(`Worker error: ${message.error}`, "bad");
    }
  };

  worker.onerror = (event) => {
    workerReady = false;
    setRuntimeStatus("Worker crashed", "error");
    log(`Worker crashed: ${event.message}`, "bad");
    setButtonsEnabled();
  };
}

function requestWorker(payload, timeoutMs = 4000) {
  if (!worker) {
    throw new Error("Python worker is not available.");
  }

  const id = ++requestId;
  const message = { ...payload, id };

  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      pendingRequests.delete(id);
      const err = new Error(`Python timed out after ${timeoutMs} ms. Check for an infinite loop or very slow search.`);
      err.isTimeout = true;
      reject(err);
    }, timeoutMs);

    pendingRequests.set(id, { resolve, reject, timer });
    worker.postMessage(message);
  });
}

async function loadStudentCode() {
  if (!workerReady) {
    log("Python runtime is still loading.", "warn");
    return false;
  }

  running = false;
  setButtonsEnabled();
  const code = codeEditor.value;
  log("Loading student code into Python worker…");

  try {
    const response = await requestWorker({ type: "load_code", code }, 8000);
    codeLoaded = true;
    lastLoadedCode = code;
    log("Student code loaded successfully.", "good");
    if (response.stdout) {
      log(`Python output while loading:\n${response.stdout}`);
    }
    setButtonsEnabled();
    return true;
  } catch (err) {
    codeLoaded = false;
    log(`Could not load student code:\n${err.message}`, "bad");
    setButtonsEnabled();
    return false;
  }
}

async function ensureCodeLoaded() {
  if (!codeLoaded || lastLoadedCode !== codeEditor.value) {
    return await loadStudentCode();
  }
  return true;
}

function parseLevel(name) {
  const rows = LEVELS[name];
  const height = rows.length;
  const width = rows[0].length;
  const walls = new Set();
  const food = new Set();
  const ghosts = [];
  let pacman = null;

  for (let y = 0; y < height; y += 1) {
    if (rows[y].length !== width) {
      throw new Error(`Level ${name} row ${y} has inconsistent width.`);
    }

    for (let x = 0; x < width; x += 1) {
      const cell = rows[y][x];
      if (cell === "#") {
        walls.add(key({ x, y }));
      } else if (cell === ".") {
        food.add(key({ x, y }));
      } else if (cell === "P") {
        pacman = { x, y };
      } else if (cell === "G") {
        ghosts.push({ x, y, startX: x, startY: y });
      }
    }
  }

  if (!pacman) {
    throw new Error(`Level ${name} has no Pacman start position.`);
  }

  return {
    name,
    width,
    height,
    walls,
    food,
    startFood: new Set(food),
    pacman: { ...pacman },
    startPacman: { ...pacman },
    ghosts: ghosts.map((ghost, index) => ({ ...ghost, id: index })),
    startGhosts: ghosts.map((ghost, index) => ({ ...ghost, id: index })),
    score: 0,
    lives: 3,
    steps: 0,
    maxSteps: 320,
    illegalMoves: 0,
    collisions: 0,
    gameOver: false,
    win: false,
    status: "Ready",
  };
}

function resetGame(name = levelSelect.value) {
  running = false;
  lastAction = "STOP";
  game = parseLevel(name);
  resizeCanvas();
  drawGame();
  updateStats();
  setButtonsEnabled();
}

function resizeCanvas() {
  canvas.width = game.width * CELL_SIZE;
  canvas.height = game.height * CELL_SIZE;
}

function key(pos) {
  return `${pos.x},${pos.y}`;
}

function keyFromArray(pos) {
  return `${pos[0]},${pos[1]}`;
}

function posFromKey(value) {
  const [x, y] = value.split(",").map(Number);
  return { x, y };
}

function nextPosition(pos, action) {
  const direction = DIRS[action] || DIRS.STOP;
  return { x: pos.x + direction.x, y: pos.y + direction.y };
}

function isWall(pos, currentGame = game) {
  if (pos.x < 0 || pos.y < 0 || pos.x >= currentGame.width || pos.y >= currentGame.height) {
    return true;
  }
  return currentGame.walls.has(key(pos));
}

function getLegalActions(pos, includeStop = true, currentGame = game) {
  const actions = [];
  for (const action of ["UP", "DOWN", "LEFT", "RIGHT"]) {
    const candidate = nextPosition(pos, action);
    if (!isWall(candidate, currentGame)) {
      actions.push(action);
    }
  }
  if (includeStop) {
    actions.push("STOP");
  }
  return actions;
}

function manhattan(a, b) {
  return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

function normalizeAction(action) {
  const normalized = String(action || "STOP").trim().toUpperCase();
  return ACTIONS.includes(normalized) ? normalized : "STOP";
}

function buildStudentState(currentGame = game) {
  return {
    pacman: [currentGame.pacman.x, currentGame.pacman.y],
    ghosts: currentGame.ghosts.map((ghost) => [ghost.x, ghost.y]),
    food: Array.from(currentGame.food).map((item) => {
      const pos = posFromKey(item);
      return [pos.x, pos.y];
    }),
    walls: Array.from(currentGame.walls).map((item) => {
      const pos = posFromKey(item);
      return [pos.x, pos.y];
    }),
    legal_actions: getLegalActions(currentGame.pacman, true, currentGame),
    score: currentGame.score,
    lives: currentGame.lives,
    steps: currentGame.steps,
    width: currentGame.width,
    height: currentGame.height,
  };
}

async function askPythonForAction(currentGame = game) {
  const state = buildStudentState(currentGame);
  const response = await requestWorker({ type: "get_action", state }, DECISION_TIMEOUT_MS);

  if (response.stdout) {
    log(`Python print output:\n${response.stdout}`);
  }

  return normalizeAction(response.action);
}

function moveGhosts(currentGame = game) {
  if (currentGame.steps % 2 !== 0) {
    return;
  }

  for (const ghost of currentGame.ghosts) {
    const legal = getLegalActions(ghost, false, currentGame);
    if (legal.length === 0) continue;

    const scored = legal.map((action) => {
      const candidate = nextPosition(ghost, action);
      const distance = manhattan(candidate, currentGame.pacman);
      const tieBreaker = (ACTIONS.indexOf(action) + currentGame.steps + ghost.id) % 4;
      return { action, candidate, distance, tieBreaker };
    });

    scored.sort((a, b) => {
      if (a.distance !== b.distance) return a.distance - b.distance;
      return a.tieBreaker - b.tieBreaker;
    });

    ghost.x = scored[0].candidate.x;
    ghost.y = scored[0].candidate.y;
  }
}

function checkCollision(currentGame = game) {
  return currentGame.ghosts.some((ghost) => ghost.x === currentGame.pacman.x && ghost.y === currentGame.pacman.y);
}

function handleCollision(currentGame = game) {
  currentGame.collisions += 1;
  currentGame.lives -= 1;
  currentGame.score -= 75;

  if (currentGame.lives <= 0) {
    currentGame.gameOver = true;
    currentGame.win = false;
    currentGame.status = "Game over: caught by a ghost";
    return;
  }

  currentGame.status = "Caught! Positions reset.";
  currentGame.pacman = { ...currentGame.startPacman };
  currentGame.ghosts = currentGame.startGhosts.map((ghost) => ({ ...ghost }));
}

function stepGame(action, currentGame = game) {
  if (currentGame.gameOver) return;

  const legalActions = getLegalActions(currentGame.pacman, true, currentGame);
  let safeAction = normalizeAction(action);

  if (!legalActions.includes(safeAction)) {
    currentGame.illegalMoves += 1;
    currentGame.score -= 5;
    safeAction = "STOP";
  }

  lastAction = safeAction;
  currentGame.steps += 1;
  currentGame.score -= 1;

  const candidate = nextPosition(currentGame.pacman, safeAction);
  if (!isWall(candidate, currentGame)) {
    currentGame.pacman = candidate;
  }

  const pacmanKey = key(currentGame.pacman);
  if (currentGame.food.has(pacmanKey)) {
    currentGame.food.delete(pacmanKey);
    currentGame.score += 15;
  }

  if (checkCollision(currentGame)) {
    handleCollision(currentGame);
    return;
  }

  moveGhosts(currentGame);

  if (checkCollision(currentGame)) {
    handleCollision(currentGame);
    return;
  }

  if (currentGame.food.size === 0) {
    currentGame.gameOver = true;
    currentGame.win = true;
    currentGame.score += 250;
    currentGame.status = "Win: all food collected";
    return;
  }

  if (currentGame.steps >= currentGame.maxSteps) {
    currentGame.gameOver = true;
    currentGame.win = false;
    currentGame.status = "Stopped: max steps reached";
    return;
  }

  currentGame.status = `Last action: ${safeAction}`;
}

async function stepOnce({ render = true } = {}) {
  if (!(await ensureCodeLoaded())) return false;
  if (game.gameOver) {
    log(`Game is over. Reset to play again. Status: ${game.status}`, "warn");
    return false;
  }

  try {
    const action = await askPythonForAction(game);
    stepGame(action, game);
    if (render) {
      drawGame();
      updateStats();
    }
    return true;
  } catch (err) {
    running = false;
    if (err.isTimeout) {
      log(err.message, "bad");
      log("Restarting the Python worker. Reload the code after fixing the loop.", "warn");
      createPythonWorker();
    } else {
      log(`Python error:\n${err.message}`, "bad");
    }
    setButtonsEnabled();
    return false;
  }
}

async function runLoop() {
  if (running) {
    running = false;
    setButtonsEnabled();
    return;
  }

  if (!(await ensureCodeLoaded())) return;

  running = true;
  setButtonsEnabled();
  log("Running simulation…");

  while (running && !game.gameOver) {
    const ok = await stepOnce({ render: true });
    if (!ok) break;
    await delay(RUN_DELAY_MS);
  }

  running = false;
  setButtonsEnabled();

  if (game.gameOver) {
    log(`${game.status}. Final score: ${game.score}`, game.win ? "good" : "warn");
  } else {
    log("Simulation paused.");
  }
}

async function runTests() {
  running = false;
  setButtonsEnabled();

  if (!(await ensureCodeLoaded())) return;

  const originalLevel = levelSelect.value;
  const results = [];
  log("Running quick tests on all maps…");

  for (const levelName of Object.keys(LEVELS)) {
    const testGame = parseLevel(levelName);

    try {
      while (!testGame.gameOver) {
        const action = await askPythonForAction(testGame);
        stepGame(action, testGame);
      }

      results.push({
        level: levelName,
        score: testGame.score,
        win: testGame.win,
        foodLeft: testGame.food.size,
        steps: testGame.steps,
        deaths: testGame.collisions,
        illegal: testGame.illegalMoves,
        status: testGame.status,
      });
    } catch (err) {
      results.push({
        level: levelName,
        score: testGame.score,
        win: false,
        foodLeft: testGame.food.size,
        steps: testGame.steps,
        deaths: testGame.collisions,
        illegal: testGame.illegalMoves,
        status: err.message,
      });
      break;
    }
  }

  levelSelect.value = originalLevel;
  resetGame(originalLevel);
  printTestResults(results);
}

function printTestResults(results) {
  const lines = [];
  lines.push("Test results");
  lines.push("------------");
  for (const result of results) {
    lines.push(
      `${result.level.padEnd(10)} score=${String(result.score).padStart(5)} ` +
      `win=${String(result.win).padEnd(5)} food_left=${String(result.foodLeft).padStart(3)} ` +
      `steps=${String(result.steps).padStart(3)} deaths=${result.deaths} illegal=${result.illegal} status=${result.status}`
    );
  }
  log(lines.join("\n"), "good");
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function drawGame() {
  if (!game) return;

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#050711";
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  drawGrid();
  drawFood();
  drawWalls();
  drawGhosts();
  drawPacman();

  if (game.gameOver) {
    drawOverlay(game.win ? "YOU WIN" : "GAME OVER", game.status);
  }
}

function drawGrid() {
  ctx.strokeStyle = "rgba(255, 255, 255, 0.04)";
  ctx.lineWidth = 1;
  for (let x = 0; x <= game.width; x += 1) {
    ctx.beginPath();
    ctx.moveTo(x * CELL_SIZE, 0);
    ctx.lineTo(x * CELL_SIZE, canvas.height);
    ctx.stroke();
  }
  for (let y = 0; y <= game.height; y += 1) {
    ctx.beginPath();
    ctx.moveTo(0, y * CELL_SIZE);
    ctx.lineTo(canvas.width, y * CELL_SIZE);
    ctx.stroke();
  }
}

function drawWalls() {
  for (const wallKey of game.walls) {
    const wall = posFromKey(wallKey);
    const x = wall.x * CELL_SIZE;
    const y = wall.y * CELL_SIZE;
    ctx.fillStyle = "#1f5eff";
    roundRect(ctx, x + 3, y + 3, CELL_SIZE - 6, CELL_SIZE - 6, 7);
    ctx.fill();
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.stroke();
  }
}

function drawFood() {
  ctx.fillStyle = "#fff3bf";
  for (const foodKey of game.food) {
    const food = posFromKey(foodKey);
    const cx = food.x * CELL_SIZE + CELL_SIZE / 2;
    const cy = food.y * CELL_SIZE + CELL_SIZE / 2;
    ctx.beginPath();
    ctx.arc(cx, cy, CELL_SIZE * 0.11, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawPacman() {
  const cx = game.pacman.x * CELL_SIZE + CELL_SIZE / 2;
  const cy = game.pacman.y * CELL_SIZE + CELL_SIZE / 2;
  const radius = CELL_SIZE * 0.38;
  const angleMap = {
    RIGHT: 0,
    DOWN: Math.PI / 2,
    LEFT: Math.PI,
    UP: Math.PI * 1.5,
    STOP: 0,
  };
  const facing = angleMap[lastAction] ?? 0;
  const mouth = 0.27 * Math.PI;

  ctx.fillStyle = "#ffd43b";
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, radius, facing + mouth, facing + Math.PI * 2 - mouth);
  ctx.closePath();
  ctx.fill();
}

function drawGhosts() {
  const colors = ["#ff6b6b", "#cc5de8", "#4dabf7", "#69db7c"];

  for (const ghost of game.ghosts) {
    const x = ghost.x * CELL_SIZE;
    const y = ghost.y * CELL_SIZE;
    const cx = x + CELL_SIZE / 2;
    const cy = y + CELL_SIZE / 2;
    ctx.fillStyle = colors[ghost.id % colors.length];

    ctx.beginPath();
    ctx.arc(cx, cy - 1, CELL_SIZE * 0.30, Math.PI, 0);
    ctx.lineTo(cx + CELL_SIZE * 0.30, cy + CELL_SIZE * 0.28);
    ctx.lineTo(cx + CELL_SIZE * 0.15, cy + CELL_SIZE * 0.18);
    ctx.lineTo(cx, cy + CELL_SIZE * 0.28);
    ctx.lineTo(cx - CELL_SIZE * 0.15, cy + CELL_SIZE * 0.18);
    ctx.lineTo(cx - CELL_SIZE * 0.30, cy + CELL_SIZE * 0.28);
    ctx.closePath();
    ctx.fill();

    ctx.fillStyle = "white";
    ctx.beginPath();
    ctx.arc(cx - 5, cy - 3, 4, 0, Math.PI * 2);
    ctx.arc(cx + 5, cy - 3, 4, 0, Math.PI * 2);
    ctx.fill();

    ctx.fillStyle = "#111827";
    ctx.beginPath();
    ctx.arc(cx - 4, cy - 3, 1.8, 0, Math.PI * 2);
    ctx.arc(cx + 6, cy - 3, 1.8, 0, Math.PI * 2);
    ctx.fill();
  }
}

function drawOverlay(title, subtitle) {
  ctx.save();
  ctx.fillStyle = "rgba(0, 0, 0, 0.62)";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.textAlign = "center";
  ctx.fillStyle = game.win ? "#b7f5ce" : "#ffc9c9";
  ctx.font = "bold 42px system-ui, sans-serif";
  ctx.fillText(title, canvas.width / 2, canvas.height / 2 - 8);
  ctx.fillStyle = "#eef2ff";
  ctx.font = "16px system-ui, sans-serif";
  ctx.fillText(subtitle, canvas.width / 2, canvas.height / 2 + 28);
  ctx.restore();
}

function roundRect(context, x, y, width, height, radius) {
  const r = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(x + r, y);
  context.arcTo(x + width, y, x + width, y + height, r);
  context.arcTo(x + width, y + height, x, y + height, r);
  context.arcTo(x, y + height, x, y, r);
  context.arcTo(x, y, x + width, y, r);
  context.closePath();
}

function updateStats() {
  const totalFood = game.startFood.size;
  const foodEaten = totalFood - game.food.size;
  const state = buildStudentState(game);
  statePreview.textContent = JSON.stringify(state, null, 2);

  statsEl.innerHTML = `
    <div class="stat-card"><span>Score</span><strong>${game.score}</strong></div>
    <div class="stat-card"><span>Lives</span><strong>${game.lives}</strong></div>
    <div class="stat-card"><span>Food</span><strong>${foodEaten}/${totalFood}</strong></div>
    <div class="stat-card"><span>Steps</span><strong>${game.steps}/${game.maxSteps}</strong></div>
    <div class="stat-card"><span>Status</span><strong>${escapeHtml(game.status)}</strong></div>
  `;
}

loadCodeBtn.addEventListener("click", loadStudentCode);
stepBtn.addEventListener("click", () => stepOnce({ render: true }));
runBtn.addEventListener("click", runLoop);
resetBtn.addEventListener("click", () => {
  resetGame();
  log("Game reset.");
});
testsBtn.addEventListener("click", runTests);
clearConsoleBtn.addEventListener("click", () => {
  consoleEl.textContent = "";
});
levelSelect.addEventListener("change", () => {
  resetGame(levelSelect.value);
  log(`Loaded map: ${levelSelect.value}`);
});

codeEditor.addEventListener("scroll", syncEditorScroll);
codeEditor.addEventListener("input", updateEditorDecorations);
["paste", "drop", "copy", "cut"].forEach((type) => {
  codeEditor.addEventListener(type, blockEditorClipboard);
});
codeEditor.addEventListener("contextmenu", (event) => event.preventDefault());
codeEditor.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();
  if ((event.ctrlKey || event.metaKey) && ["v", "c", "x"].includes(key)) {
    blockEditorClipboard(event);
    return;
  }
  handleEditorCommand(event);
});

updateEditorDecorations();
resetGame();
createPythonWorker();
setButtonsEnabled();
log("Open this page from a local web server, not file://. See README.md.", "warn");
