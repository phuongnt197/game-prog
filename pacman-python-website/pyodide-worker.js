/*
  Runs student Python inside a Web Worker.
  The main thread owns the Pacman game and canvas rendering.
*/

const PYODIDE_VERSION = "0.29.4";
const PYODIDE_BASE_URL = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full/`;

importScripts(`${PYODIDE_BASE_URL}pyodide.js`);

const SUPPORT_CODE = `
VALID_ACTIONS = ["UP", "DOWN", "LEFT", "RIGHT", "STOP"]
DIRECTIONS = {
    "UP": (0, -1),
    "DOWN": (0, 1),
    "LEFT": (-1, 0),
    "RIGHT": (1, 0),
    "STOP": (0, 0),
}


def move(position, action):
    action = str(action).upper()
    dx, dy = DIRECTIONS.get(action, (0, 0))
    x, y = position
    return (x + dx, y + dy)


def next_position(position, action):
    return move(position, action)


def manhattan_distance(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def nearest_food(pacman, food):
    if not food:
        return None
    return min(food, key=lambda pellet: manhattan_distance(pacman, pellet))


def legal_neighbors(position, walls):
    result = []
    for action in ["UP", "DOWN", "LEFT", "RIGHT"]:
        neighbor = move(position, action)
        if neighbor not in walls:
            result.append((action, neighbor))
    return result
`;

let pyodidePromise = null;
let pyodide = null;

function truncate(text, maxLength = 12000) {
  if (!text) return "";
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + "\n... output truncated ...";
}

async function initPyodide() {
  pyodide = await loadPyodide({ indexURL: PYODIDE_BASE_URL });
  self.postMessage({ type: "ready", pyodideVersion: PYODIDE_VERSION });
  return pyodide;
}

pyodidePromise = initPyodide().catch((err) => {
  self.postMessage({ type: "fatal", error: String(err) });
});

async function ensurePyodide() {
  if (pyodide) return pyodide;
  await pyodidePromise;
  if (!pyodide) throw new Error("Pyodide failed to initialize.");
  return pyodide;
}

async function loadStudentCode(id, code) {
  const py = await ensurePyodide();
  py.globals.set("support_code", SUPPORT_CODE);
  py.globals.set("student_code", code);

  const resultJson = await py.runPythonAsync(`
import inspect, json, sys, io, traceback
_stdout = io.StringIO()
_old_stdout = sys.stdout
sys.stdout = _stdout
try:
    student_ns = {"__name__": "__student__"}
    exec(support_code, student_ns)
    exec(student_code, student_ns)
    if "choose_action" not in student_ns:
        raise Exception("Define choose_action(pacman, food, ghosts, walls, legal_actions).")
    if not callable(student_ns["choose_action"]):
        raise Exception("choose_action must be a function.")
    try:
        inspect.signature(student_ns["choose_action"]).bind((1, 1), [], [], [], ["STOP"])
    except TypeError:
        raise Exception("choose_action must accept these five inputs: pacman, food, ghosts, walls, legal_actions.")
    globals()["student_ns"] = student_ns
    _result = {"ok": True, "stdout": _stdout.getvalue()}
except Exception:
    _result = {"ok": False, "stdout": _stdout.getvalue(), "error": traceback.format_exc()}
finally:
    sys.stdout = _old_stdout
json.dumps(_result)
`);

  const result = JSON.parse(resultJson);
  self.postMessage({
    id,
    type: "loaded",
    ok: result.ok,
    stdout: truncate(result.stdout),
    error: result.error || "",
  });
}

async function getAction(id, state) {
  const py = await ensurePyodide();
  py.globals.set("state_json", JSON.stringify(state));

  const resultJson = await py.runPythonAsync(`
import json, sys, io, traceback
_stdout = io.StringIO()
_old_stdout = sys.stdout
sys.stdout = _stdout
try:
    if "student_ns" not in globals():
        raise Exception("Student code has not been loaded.")
    data = json.loads(state_json)
    pacman = tuple(data.get("pacman", (0, 0)))
    food = [tuple(position) for position in data.get("food", [])]
    ghosts = [tuple(position) for position in data.get("ghosts", [])]
    walls = [tuple(position) for position in data.get("walls", [])]
    legal_actions = list(data.get("legal_actions", []))
    action = student_ns["choose_action"](pacman, food, ghosts, walls, legal_actions)
    _result = {"ok": True, "action": str(action).upper(), "stdout": _stdout.getvalue()}
except Exception:
    _result = {"ok": False, "action": "STOP", "stdout": _stdout.getvalue(), "error": traceback.format_exc()}
finally:
    sys.stdout = _old_stdout
json.dumps(_result)
`);

  const result = JSON.parse(resultJson);
  self.postMessage({
    id,
    type: "action",
    ok: result.ok,
    action: result.action || "STOP",
    stdout: truncate(result.stdout),
    error: result.error || "",
  });
}

self.onmessage = async (event) => {
  const message = event.data || {};
  const id = message.id;

  try {
    if (message.type === "load_code") {
      await loadStudentCode(id, message.code || "");
      return;
    }

    if (message.type === "get_action") {
      await getAction(id, message.state || {});
      return;
    }

    self.postMessage({ id, type: "error", ok: false, error: `Unknown worker message type: ${message.type}` });
  } catch (err) {
    self.postMessage({ id, type: "error", ok: false, error: String(err) });
  }
};
