import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  CUSTOM_LEVEL_ID,
  CUSTOM_LEVEL_ROWS,
  DECISION_TIMEOUT_MS,
  LEVELS,
  REQUIRED_LEVEL_IDS,
  RUN_DELAY_MS,
  STARTER_CODE,
} from "../game/constants";
import { buildStudentInputs, gradeGame, normalizeAction, parseLevel, stepGame } from "../game/engine";
import { cloneRows, validateCustomLevel } from "../game/levelDesigner";
import { PythonRuntime } from "../runtime/PythonRuntime";

const CODE_STORAGE_KEY = "aip1-pacman-code-v2";
const LEVEL_STORAGE_KEY = "aip1-pacman-custom-level-v1";
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

function loadSavedCode(key) {
  try {
    return localStorage.getItem(key) || STARTER_CODE;
  } catch {
    return STARTER_CODE;
  }
}

function loadSavedLevel(key) {
  try {
    const rows = JSON.parse(localStorage.getItem(key) || "null");
    const width = Array.isArray(rows) ? rows[0]?.length : 0;
    const editable = Array.isArray(rows) && rows.length >= 6 && width >= 8
      && rows.every((row) => typeof row === "string" && row.length === width && /^[#.PG ]+$/.test(row));
    return editable ? cloneRows(rows) : cloneRows(CUSTOM_LEVEL_ROWS);
  } catch {
    return cloneRows(CUSTOM_LEVEL_ROWS);
  }
}

function saveLocal(key, value) {
  try {
    localStorage.setItem(key, typeof value === "string" ? value : JSON.stringify(value));
  } catch {
    // Local storage can be disabled; the current browser session still works.
  }
}

export function usePacmanGame(storageScope = "local") {
  const codeStorageKey = useRef(`${CODE_STORAGE_KEY}-${storageScope}`).current;
  const levelStorageKey = useRef(`${LEVEL_STORAGE_KEY}-${storageScope}`).current;
  const [code, setCode] = useState(() => loadSavedCode(codeStorageKey));
  const codeRef = useRef(code);
  const [customRows, setCustomRowsState] = useState(() => loadSavedLevel(levelStorageKey));
  const customRowsRef = useRef(customRows);
  const customValidation = useMemo(() => validateCustomLevel(customRows), [customRows]);
  const [level, setLevelState] = useState("training");
  const levelRef = useRef(level);
  const gameRef = useRef(parseLevel("training"));
  const [game, setGame] = useState(gameRef.current);
  const [lastAction, setLastAction] = useState("STOP");
  const [running, setRunning] = useState(false);
  const runningRef = useRef(false);
  const [evaluating, setEvaluating] = useState(false);
  const [evaluationProgress, setEvaluationProgress] = useState("");
  const [evaluation, setEvaluation] = useState([]);
  const [runtimeStatus, setRuntimeStatus] = useState({ ready: false, text: "Loading Pyodide…", mode: "loading" });
  const [logs, setLogs] = useState([]);
  const loadedCodeRef = useRef("");
  const runtimeRef = useRef(null);

  const log = useCallback((message, kind = "") => setLogs((items) => [...items, {
    id: crypto.randomUUID(),
    time: new Date().toLocaleTimeString(),
    message,
    kind,
  }]), []);
  const refreshGame = () => setGame({ ...gameRef.current });
  const stopRunning = () => {
    runningRef.current = false;
    setRunning(false);
  };
  const makeGame = useCallback((name) => parseLevel(name, customRowsRef.current), []);

  useEffect(() => {
    const runtime = new PythonRuntime({
      onStatus: (status) => {
        setRuntimeStatus(status);
        if (status.ready) log("Python is ready. Load your function, then run a map or evaluate the bot.", "good");
      },
      onOutput: log,
    });
    runtimeRef.current = runtime;
    runtime.start();
    return () => runtime.stop();
  }, [log]);

  const updateCode = (value) => {
    codeRef.current = value;
    setCode(value);
    saveLocal(codeStorageKey, value);
    setEvaluation([]);
  };

  const loadCode = useCallback(async () => {
    if (!runtimeStatus.ready) {
      log("Python is still loading.", "warn");
      return false;
    }
    stopRunning();
    log("Loading choose_action into Python…");
    try {
      const response = await runtimeRef.current.request({ type: "load_code", code: codeRef.current }, 8000);
      loadedCodeRef.current = codeRef.current;
      log("Bot function loaded successfully.", "good");
      if (response.stdout) log(`Python output while loading:\n${response.stdout}`);
      return true;
    } catch (error) {
      loadedCodeRef.current = "";
      log(`Could not load the bot function:\n${error.message}`, "bad");
      return false;
    }
  }, [log, runtimeStatus.ready]);

  const ensureCode = useCallback(
    () => loadedCodeRef.current === codeRef.current ? Promise.resolve(true) : loadCode(),
    [loadCode],
  );

  const askForAction = useCallback(async (targetGame) => {
    const response = await runtimeRef.current.request(
      { type: "get_action", state: buildStudentInputs(targetGame) },
      DECISION_TIMEOUT_MS,
    );
    if (response.stdout) log(`Python print output:\n${response.stdout}`);
    return normalizeAction(response.action);
  }, [log]);

  const step = useCallback(async (targetGame = gameRef.current, render = true) => {
    if (!(await ensureCode())) return false;
    if (targetGame.gameOver) {
      log(`This run is over. Reset to try again. Status: ${targetGame.status}`, "warn");
      return false;
    }
    try {
      const action = await askForAction(targetGame);
      const applied = stepGame(targetGame, action);
      if (targetGame === gameRef.current) setLastAction(applied);
      if (render) refreshGame();
      return true;
    } catch (error) {
      stopRunning();
      log(error.isTimeout ? error.message : `Python error:\n${error.message}`, "bad");
      if (error.isTimeout) {
        log("Restarting Python. Fix the slow or infinite loop, then load the function again.", "warn");
        loadedCodeRef.current = "";
        runtimeRef.current.start();
      }
      return false;
    }
  }, [askForAction, ensureCode, log]);

  const toggleRun = useCallback(async () => {
    if (runningRef.current) {
      stopRunning();
      return;
    }
    if (!(await ensureCode())) return;
    runningRef.current = true;
    setRunning(true);
    log(`Running ${gameRef.current.label}…`);
    while (runningRef.current && !gameRef.current.gameOver) {
      if (!(await step(gameRef.current, true))) break;
      await delay(RUN_DELAY_MS);
    }
    const finished = gameRef.current.gameOver;
    stopRunning();
    const result = gradeGame(gameRef.current);
    log(
      finished ? `${gameRef.current.status}. Score ${result.score}; target ${result.targetScore}.` : "Simulation paused.",
      finished && result.passed ? "good" : "warn",
    );
  }, [ensureCode, log, step]);

  const reset = useCallback((name = levelRef.current, announce = true) => {
    stopRunning();
    loadedCodeRef.current = "";
    gameRef.current = makeGame(name);
    setLastAction("STOP");
    refreshGame();
    if (announce) log("Simulation reset.");
  }, [log, makeGame]);

  const setLevel = useCallback((name) => {
    if (name === CUSTOM_LEVEL_ID && !validateCustomLevel(customRowsRef.current).valid) {
      log("Finish the custom map before trying to play it.", "warn");
      return;
    }
    levelRef.current = name;
    setLevelState(name);
    reset(name, false);
    log(`Loaded map: ${name === CUSTOM_LEVEL_ID ? "My Level" : LEVELS[name].label}`);
  }, [log, reset]);

  const updateCustomRows = useCallback((rows) => {
    const nextRows = cloneRows(rows);
    customRowsRef.current = nextRows;
    setCustomRowsState(nextRows);
    saveLocal(levelStorageKey, nextRows);
    setEvaluation([]);
    if (levelRef.current === CUSTOM_LEVEL_ID && validateCustomLevel(nextRows).valid) reset(CUSTOM_LEVEL_ID, false);
  }, [levelStorageKey, reset]);

  const evaluateBot = useCallback(async () => {
    stopRunning();
    const validation = validateCustomLevel(customRowsRef.current);
    if (!validation.valid) {
      log(`The custom map is not ready:\n- ${validation.errors.join("\n- ")}`, "bad");
      return;
    }
    if (!(await ensureCode())) return;
    const levelIds = [...REQUIRED_LEVEL_IDS, CUSTOM_LEVEL_ID];
    const results = [];
    let aborted = false;
    setEvaluation([]);
    setEvaluating(true);
    try {
      for (const name of levelIds) {
        const testGame = makeGame(name);
        setEvaluationProgress(`Testing ${testGame.label}…`);
        try {
          loadedCodeRef.current = "";
          await runtimeRef.current.request({ type: "load_code", code: codeRef.current }, 8000);
          loadedCodeRef.current = codeRef.current;
          while (!testGame.gameOver) {
            const action = await askForAction(testGame);
            stepGame(testGame, action);
          }
        } catch (error) {
          testGame.status = error.isTimeout ? error.message : `Python error: ${error.message}`;
          if (error.isTimeout || !loadedCodeRef.current) {
            loadedCodeRef.current = "";
            if (error.isTimeout) runtimeRef.current.start();
            aborted = true;
          }
        }
        results.push(gradeGame(testGame));
        setEvaluation([...results]);
        if (aborted) break;
      }
      const tested = new Set(results.map((result) => result.id));
      levelIds.filter((name) => !tested.has(name)).forEach((name) => {
        const skipped = makeGame(name);
        results.push({ ...gradeGame(skipped), status: "Not run because Python stopped." });
      });
      setEvaluation(results);
      const passed = results.filter((result) => result.passed).length;
      const report = results.map((result) => `${result.passed ? "PASS" : "FAIL"} ${result.label}: score ${result.score}/${result.targetScore}, win=${result.win}`).join("\n");
      log(`Bot evaluation: ${passed}/${results.length} challenges passed\n${report}`, passed === results.length ? "good" : "warn");
    } finally {
      setEvaluating(false);
      setEvaluationProgress("");
      reset(levelRef.current, false);
    }
  }, [askForAction, ensureCode, log, makeGame, reset]);

  const requiredChallengeCount = REQUIRED_LEVEL_IDS.length + 1;
  const passedChallengeCount = evaluation.filter((result) => result.passed).length;
  return {
    code,
    updateCode,
    level,
    setLevel,
    customRows,
    customValidation,
    updateCustomRows,
    game,
    lastAction,
    running,
    evaluating,
    evaluationProgress,
    evaluation,
    requiredChallengeCount,
    passedChallengeCount,
    runtimeStatus,
    logs,
    clearLogs: () => setLogs([]),
    log,
    loadCode,
    step: () => step(),
    toggleRun,
    reset,
    evaluateBot,
  };
}
