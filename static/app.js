const state = {
  user: null,
  assignments: [],
  currentAssignment: null,
  currentResult: null,
  templates: [],
  templateId: "adventure",
  actionHistory: [],
  busy: false,
  behavior: [],
  lastEditorValue: "",
  lastEditAt: Date.now(),
  suppressInput: false,
  editorSnapshots: new WeakMap(),
  autosaveTimer: null,
  lastSavedDraft: "",
  currentCaseIndex: 0,
};

const els = {
  authScreen: document.querySelector("#authScreen"),
  appShell: document.querySelector("#appShell"),
  userLine: document.querySelector("#userLine"),
  adminNav: document.querySelector("#adminNav"),
  loginForm: document.querySelector("#loginForm"),
  registerForm: document.querySelector("#registerForm"),
  assignmentList: document.querySelector("#assignmentList"),
  roadmapProgress: document.querySelector("#roadmapProgress"),
  missionStage: document.querySelector("#missionStage"),
  missionTitle: document.querySelector("#missionTitle"),
  missionSummary: document.querySelector("#missionSummary"),
  missionStatus: document.querySelector("#missionStatus"),
  missionInstructions: document.querySelector("#missionInstructions"),
  missionEditor: document.querySelector("#missionEditor"),
  missionLineNumbers: document.querySelector("#missionLineNumbers"),
  missionHighlight: document.querySelector("#missionHighlight"),
  missionRunBtn: document.querySelector("#missionRunBtn"),
  missionSubmitBtn: document.querySelector("#missionSubmitBtn"),
  missionSaveBtn: document.querySelector("#missionSaveBtn"),
  missionResetBtn: document.querySelector("#missionResetBtn"),
  missionCaseSelect: document.querySelector("#missionCaseSelect"),
  telemetryState: document.querySelector("#telemetryState"),
  agentGrid: document.querySelector("#agentGrid"),
  agentCaption: document.querySelector("#agentCaption"),
  checkList: document.querySelector("#checkList"),
  missionConsole: document.querySelector("#missionConsole"),
  replayBtn: document.querySelector("#replayBtn"),
  templateButtons: document.querySelector("#templateButtons"),
  projectTitle: document.querySelector("#projectTitle"),
  projectCreator: document.querySelector("#projectCreator"),
  projectDescription: document.querySelector("#projectDescription"),
  specEditor: document.querySelector("#specEditor"),
  aiRecord: document.querySelector("#aiRecord"),
  codeEditor: document.querySelector("#codeEditor"),
  testEditor: document.querySelector("#testEditor"),
  codeEditorShell: document.querySelector("#codeEditorShell"),
  testEditorShell: document.querySelector("#testEditorShell"),
  codeLineNumbers: document.querySelector("#codeLineNumbers"),
  testLineNumbers: document.querySelector("#testLineNumbers"),
  codeHighlight: document.querySelector("#codeHighlight"),
  testHighlight: document.querySelector("#testHighlight"),
  studioLocked: document.querySelector("#studioLocked"),
  studioWorkspace: document.querySelector("#studioWorkspace"),
  playTitle: document.querySelector("#playTitle"),
  scoreBadge: document.querySelector("#scoreBadge"),
  statusBanner: document.querySelector("#statusBanner"),
  stateText: document.querySelector("#stateText"),
  actionButtons: document.querySelector("#actionButtons"),
  stateJson: document.querySelector("#stateJson"),
  testResults: document.querySelector("#testResults"),
  consoleOutput: document.querySelector("#consoleOutput"),
  projectGrid: document.querySelector("#projectGrid"),
  pacmanFrame: document.querySelector("#pacmanFrame"),
  adminUsersTable: document.querySelector("#adminUsersTable"),
  adminSubmissionsTable: document.querySelector("#adminSubmissionsTable"),
  adminCreateUserForm: document.querySelector("#adminCreateUserForm"),
  changePasswordForm: document.querySelector("#changePasswordForm"),
  toast: document.querySelector("#toast"),
};

window.addEventListener("unhandledrejection", (event) => {
  const message = event.reason && event.reason.message ? event.reason.message : String(event.reason || "Request failed");
  showToast(message);
});

bindEvents();
init();

function bindEvents() {
  els.loginForm.addEventListener("submit", login);
  els.registerForm.addEventListener("submit", register);
  els.changePasswordForm.addEventListener("submit", changePassword);
  els.adminCreateUserForm.addEventListener("submit", adminCreateUser);
  document.querySelector("#logoutBtn").addEventListener("click", logout);
  document.querySelector("#refreshAdminBtn").addEventListener("click", loadAdmin);
  document.querySelector("#refreshProjectsBtn").addEventListener("click", loadProjects);
  els.missionRunBtn.addEventListener("click", () => runMission(false));
  els.missionSubmitBtn.addEventListener("click", () => runMission(true));
  els.missionSaveBtn.addEventListener("click", () => saveMissionDraft(true));
  els.missionResetBtn.addEventListener("click", resetMission);
  els.missionCaseSelect.addEventListener("change", () => {
    state.currentCaseIndex = Number(els.missionCaseSelect.value || 0);
    const selectedCase = selectedMissionCase();
    renderWorld(selectedCase?.world || state.currentAssignment?.world, null);
    els.checkList.innerHTML = "";
    els.missionConsole.textContent = "";
  });
  els.replayBtn.addEventListener("click", () => animateTrace(state.currentResult));

  document.querySelectorAll(".nav-tab").forEach((button) => {
    button.addEventListener("click", () => switchView(button.dataset.view));
  });
  document.querySelectorAll(".editor-tab").forEach((button) => {
    button.addEventListener("click", () => switchProjectEditor(button.dataset.editor));
  });

  document.querySelector("#runBtn").addEventListener("click", () => runProject(false));
  document.querySelector("#resetBtn").addEventListener("click", resetProject);
  document.querySelector("#testBtn").addEventListener("click", runProjectTests);
  document.querySelector("#aiCodeBtn").addEventListener("click", () => askAI("code"));
  document.querySelector("#aiTestsBtn").addEventListener("click", () => askAI("tests"));
  document.querySelector("#feedbackBtn").addEventListener("click", () => askAI("feedback"));
  document.querySelector("#publishBtn").addEventListener("click", publishProject);

  bindProtectedEditor(els.missionEditor, () => state.currentAssignment?.id || "roadmap", els.missionLineNumbers, els.missionHighlight, "python");
  bindProtectedEditor(els.codeEditor, () => "project-studio", els.codeLineNumbers, els.codeHighlight, "python");
  bindProtectedEditor(els.testEditor, () => "project-studio-tests", els.testLineNumbers, els.testHighlight, "json");
  window.addEventListener("beforeunload", () => flushBehavior(true));
  window.setInterval(() => flushBehavior(false), 6000);
}

async function init() {
  try {
    const data = await apiGet("/api/me");
    if (!data.user) {
      showAuth();
      return;
    }
    state.user = data.user;
    showApp();
    await loadAssignments();
    await loadProjects();
    if (state.user.role === "admin") await loadAdmin();
  } catch (error) {
    showAuth();
  }
}

function showAuth() {
  els.authScreen.classList.remove("hidden");
  els.appShell.classList.add("hidden");
}

function showApp() {
  els.authScreen.classList.add("hidden");
  els.appShell.classList.remove("hidden");
  els.userLine.textContent = `${state.user.display_name} (${state.user.role})`;
  els.adminNav.classList.toggle("hidden", state.user.role !== "admin");
  if (state.user.must_change_password) switchView("account");
}

async function login(event) {
  event.preventDefault();
  const user = await apiPost("/api/auth/login", {
    username: document.querySelector("#loginUsername").value,
    password: document.querySelector("#loginPassword").value,
  }).then((data) => data.user);
  state.user = user;
  showApp();
  await loadAssignments();
  await loadProjects();
  if (state.user.role === "admin") await loadAdmin();
}

async function register(event) {
  event.preventDefault();
  const user = await apiPost("/api/auth/register", {
    display_name: document.querySelector("#registerName").value,
    username: document.querySelector("#registerUsername").value,
    password: document.querySelector("#registerPassword").value,
  }).then((data) => data.user);
  state.user = user;
  showApp();
  await loadAssignments();
  showToast("Student account created.");
}

async function logout() {
  await flushBehavior(false);
  await apiPost("/api/auth/logout", {});
  state.user = null;
  showAuth();
}

async function changePassword(event) {
  event.preventDefault();
  const data = await apiPost("/api/auth/change-password", {
    old_password: document.querySelector("#oldPassword").value,
    new_password: document.querySelector("#newPassword").value,
  });
  state.user = data.user;
  showToast("Password changed.");
  showApp();
}

async function loadAssignments() {
  const data = await apiGet("/api/assignments");
  state.assignments = data.assignments || [];
  renderAssignments();
  const active = state.assignments.find((item) => item.unlocked && !item.completed && !item.is_project)
    || state.assignments.find((item) => item.unlocked && !item.is_project)
    || state.assignments[0];
  if (active) selectAssignment(active.id);
  updateStudioLock();
}

function renderAssignments() {
  const countable = state.assignments.filter((item) => !item.is_project);
  const completed = countable.filter((item) => item.completed).length;
  els.roadmapProgress.textContent = `${completed}/${countable.length}`;
  els.assignmentList.innerHTML = "";
  let currentWeek = null;
  for (const assignment of state.assignments) {
    if (assignment.week !== currentWeek) {
      currentWeek = assignment.week;
      const heading = document.createElement("div");
      heading.className = "week-heading";
      const weekLabel = assignment.week ? `Week ${assignment.week}` : "Project";
      heading.innerHTML = `<strong>${escapeHtml(weekLabel)}</strong><span>${escapeHtml(assignment.stage)}</span>`;
      els.assignmentList.appendChild(heading);
    }

    const button = document.createElement("button");
    button.type = "button";
    button.className = "assignment-card";
    if (!assignment.unlocked) button.classList.add("locked");
    if (state.currentAssignment?.id === assignment.id) button.classList.add("is-active");
    const status = assignment.completed ? "Complete" : assignment.unlocked ? "Open" : "Locked";
    const meta = [assignment.concept, assignment.exercise_type].filter(Boolean).join(" · ");
    button.innerHTML = `<strong>${escapeHtml(assignment.order)}. ${escapeHtml(assignment.title)}</strong><span>${escapeHtml(status)} · ${escapeHtml(meta)}</span>`;
    button.addEventListener("click", () => {
      if (!assignment.unlocked) {
        showToast("This assignment is locked.");
        return;
      }
      if (assignment.is_project) {
        switchView("studio");
        return;
      }
      selectAssignment(assignment.id);
    });
    els.assignmentList.appendChild(button);
  }
}

function selectAssignment(assignmentId) {
  const assignment = state.assignments.find((item) => item.id === assignmentId);
  if (!assignment || !assignment.unlocked || assignment.is_project) return;
  state.currentAssignment = assignment;
  state.currentResult = null;
  state.currentCaseIndex = firstCaseIndex(assignment);
  renderAssignments();
  els.missionStage.textContent = `${assignment.stage} · ${assignment.part || ""}`;
  els.missionTitle.textContent = assignment.title;
  els.missionSummary.textContent = [assignment.summary, assignment.exercise_type].filter(Boolean).join(" · ");
  els.missionInstructions.textContent = assignment.instructions;
  els.missionStatus.textContent = assignment.completed ? "Complete" : "Open";
  els.missionStatus.className = `status-pill ${assignment.completed ? "done" : "open"}`;
  setEditorValue(els.missionEditor, assignment.draft_code ?? assignment.starter_code ?? "");
  state.lastSavedDraft = els.missionEditor.value;
  renderCaseOptions(assignment);
  renderWorld(selectedMissionCase()?.world || assignment.world, null);
  els.checkList.innerHTML = "";
  els.missionConsole.textContent = "";
}

function renderCaseOptions(assignment) {
  const cases = assignment.cases && assignment.cases.length ? assignment.cases : [{ index: 0, name: "Map 1", world: assignment.world }];
  els.missionCaseSelect.innerHTML = "";
  for (const item of cases) {
    const option = document.createElement("option");
    option.value = String(item.index);
    option.textContent = item.name;
    els.missionCaseSelect.appendChild(option);
  }
  els.missionCaseSelect.value = String(state.currentCaseIndex);
  els.missionCaseSelect.disabled = cases.length <= 1;
  els.missionSubmitBtn.title = assignment.case_count > 1 ? `Submit runs all ${assignment.case_count} maps.` : "Submit runs the assignment checks.";
}

function firstCaseIndex(assignment) {
  return assignment.cases && assignment.cases.length ? Number(assignment.cases[0].index) : 0;
}

function selectedMissionCase() {
  if (!state.currentAssignment) return null;
  const cases = state.currentAssignment.cases || [];
  return cases.find((item) => Number(item.index) === Number(state.currentCaseIndex)) || cases[0] || null;
}

function resetMission() {
  if (!state.currentAssignment) return;
  setEditorValue(els.missionEditor, state.currentAssignment.starter_code || "");
  state.lastSavedDraft = els.missionEditor.value;
  renderWorld(selectedMissionCase()?.world || state.currentAssignment.world, null);
  els.checkList.innerHTML = "";
  els.missionConsole.textContent = "";
  recordBehavior("reset", 0, 0, els.missionEditor.value.length, { source: "button" });
}

async function runMission(submit) {
  if (!state.currentAssignment) return;
  setBusy(true);
  recordBehavior(submit ? "submit" : "run", 0, 0, els.missionEditor.value.length, {});
  await flushBehavior(false);
  try {
    await saveMissionDraft(false);
    const endpoint = `/api/assignments/${encodeURIComponent(state.currentAssignment.id)}/${submit ? "submit" : "run"}`;
    const payload = submit ? { code: els.missionEditor.value } : { code: els.missionEditor.value, case_index: state.currentCaseIndex };
    const result = await apiPost(endpoint, payload);
    renderMissionResult(result);
    if (submit && result.completed) {
      state.lastSavedDraft = els.missionEditor.value;
      showToast("Assignment complete. Next mission unlocked.");
      await loadAssignments();
    }
  } catch (error) {
    showToast(error.message);
  } finally {
    setBusy(false);
  }
}

async function saveMissionDraft(showMessage) {
  if (!state.currentAssignment || state.currentAssignment.is_project) return;
  const code = els.missionEditor.value;
  if (!showMessage && code === state.lastSavedDraft) return;
  const assignmentId = state.currentAssignment.id;
  const result = await apiPost(`/api/assignments/${encodeURIComponent(assignmentId)}/draft`, { code });
  state.lastSavedDraft = code;
  state.currentAssignment.draft_code = code;
  state.currentAssignment.draft_updated_at = result.updated_at;
  if (showMessage) showToast("Code saved.");
}

function scheduleMissionAutosave() {
  if (!state.currentAssignment || state.currentAssignment.is_project) return;
  window.clearTimeout(state.autosaveTimer);
  state.autosaveTimer = window.setTimeout(() => {
    saveMissionDraft(false).catch((error) => showToast(error.message));
  }, 1800);
}

function renderMissionResult(result) {
  state.currentResult = result;
  if (Number.isFinite(Number(result.case_index))) {
    state.currentCaseIndex = Number(result.case_index);
    if (els.missionCaseSelect.value !== String(state.currentCaseIndex)) {
      els.missionCaseSelect.value = String(state.currentCaseIndex);
    }
  }
  renderChecks(result.checks || []);
  els.missionConsole.textContent = [result.stdout || "", result.error || ""].filter(Boolean).join("\n");
  animateTrace(result);
}

function renderChecks(checks) {
  els.checkList.innerHTML = "";
  for (const check of checks) {
    const row = document.createElement("div");
    row.className = `check-item ${check.passed ? "pass" : "fail"}`;
    row.innerHTML = `<strong>${check.passed ? "Pass" : "Fix"}: ${escapeHtml(check.name)}</strong><p>${escapeHtml(check.details || "")}</p>`;
    els.checkList.appendChild(row);
  }
}

function renderWorld(world, step) {
  if (!world) {
    els.agentGrid.innerHTML = "";
    return;
  }
  const snapshot = step || { x: world.start[0], y: world.start[1], gems: world.gems || [], action: "start", detail: "Start" };
  const gems = new Set((snapshot.gems || []).map((item) => `${item[0]},${item[1]}`));
  const walls = new Set((world.walls || []).map((item) => `${item[0]},${item[1]}`));
  const gemValues = world.gem_values || {};
  els.agentGrid.style.gridTemplateColumns = `repeat(${world.width}, 1fr)`;
  els.agentGrid.style.gridTemplateRows = `repeat(${world.height}, 1fr)`;
  els.agentGrid.innerHTML = "";
  for (let y = 0; y < world.height; y += 1) {
    for (let x = 0; x < world.width; x += 1) {
      const cell = document.createElement("div");
      cell.className = "cell";
      const key = `${x},${y}`;
      if (walls.has(key)) cell.classList.add("wall");
      if (world.goal[0] === x && world.goal[1] === y) cell.classList.add("goal");
      if (gems.has(key)) {
        cell.classList.add("gem");
        if (Object.prototype.hasOwnProperty.call(gemValues, key)) {
          const value = Number(gemValues[key]);
          cell.dataset.value = value > 0 ? `+${value}` : String(value);
          if (value < 0) cell.classList.add("bad-gem");
        }
      }
      if (snapshot.x === x && snapshot.y === y) cell.classList.add("agent");
      els.agentGrid.appendChild(cell);
    }
  }
  const scoreText = Number.isFinite(Number(snapshot.score)) ? ` · Score ${snapshot.score}` : "";
  els.agentCaption.textContent = `${snapshot.action || "start"}: ${snapshot.detail || ""}${scoreText}`;
}

function animateTrace(result) {
  if (!result || !result.world) return;
  const trace = result.trace && result.trace.length ? result.trace : [{ x: result.world.start[0], y: result.world.start[1], gems: result.world.gems, action: "start", detail: "Start" }];
  window.clearInterval(animateTrace.timer);
  let index = 0;
  renderWorld(result.world, trace[index]);
  animateTrace.timer = window.setInterval(() => {
    index += 1;
    if (index >= trace.length) {
      window.clearInterval(animateTrace.timer);
      return;
    }
    renderWorld(result.world, trace[index]);
  }, 420);
}

function bindProtectedEditor(editor, assignmentIdFn, lineNumbers, highlightLayer, language) {
  setEditorSnapshot(editor);
  updateEditorDecorations(editor, lineNumbers, highlightLayer, language);
  editor.addEventListener("paste", (event) => blockClipboard(event, "paste_attempt", assignmentIdFn));
  editor.addEventListener("drop", (event) => blockClipboard(event, "drop_attempt", assignmentIdFn));
  editor.addEventListener("copy", (event) => blockClipboard(event, "copy_attempt", assignmentIdFn));
  editor.addEventListener("cut", (event) => blockClipboard(event, "cut_attempt", assignmentIdFn));
  editor.addEventListener("contextmenu", (event) => event.preventDefault());
  editor.addEventListener("scroll", () => syncEditorScroll(editor, lineNumbers, highlightLayer));
  editor.addEventListener("keydown", (event) => {
    const key = event.key.toLowerCase();
    if ((event.ctrlKey || event.metaKey) && ["v", "c", "x"].includes(key)) {
      event.preventDefault();
      recordBehavior(`${key}_shortcut_blocked`, 0, 0, editor.value.length, { assignment_id: assignmentIdFn() });
      showToast("Copy and paste are disabled in code editors.");
      return;
    }
    if (handleEditorCommand(event, editor)) {
      recordBehavior("editor_command", 0, 0, editor.value.length, { key_class: keyClass(event.key), assignment_id: assignmentIdFn() });
      return;
    }
    recordBehavior("keydown", 0, 0, editor.value.length, { key_class: keyClass(event.key), assignment_id: assignmentIdFn() });
  });
  editor.addEventListener("input", () => {
    updateEditorDecorations(editor, lineNumbers, highlightLayer, language);
    if (state.suppressInput) return;
    const now = Date.now();
    const snapshot = getEditorSnapshot(editor);
    const diff = diffStats(snapshot.value, editor.value);
    recordBehavior("input", diff.inserted, diff.deleted, editor.value.length, {
      input_ms: now - snapshot.at,
      assignment_id: assignmentIdFn(),
    });
    setEditorSnapshot(editor, now);
    if (editor === els.missionEditor) scheduleMissionAutosave();
  });
  editor.addEventListener("focus", () => {
    setEditorSnapshot(editor);
    recordBehavior("focus", 0, 0, editor.value.length, { assignment_id: assignmentIdFn() });
  });
  editor.addEventListener("blur", () => {
    recordBehavior("blur", 0, 0, editor.value.length, { assignment_id: assignmentIdFn() });
    flushBehavior(false);
  });
}

const EDITOR_INDENT = "    ";

function handleEditorCommand(event, editor) {
  if (event.key === "Tab") {
    event.preventDefault();
    if (event.shiftKey) {
      unindentSelection(editor);
    } else {
      indentSelection(editor);
    }
    return true;
  }
  if (event.key === "Enter") {
    event.preventDefault();
    insertAutoIndent(editor);
    return true;
  }
  if (event.key === "Backspace" && editor.selectionStart === editor.selectionEnd && shouldSmartOutdent(editor)) {
    event.preventDefault();
    const cursor = editor.selectionStart;
    replaceEditorRange(editor, cursor - EDITOR_INDENT.length, cursor, "", cursor - EDITOR_INDENT.length, cursor - EDITOR_INDENT.length);
    return true;
  }
  return false;
}

function indentSelection(editor) {
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  if (start === end) {
    replaceEditorRange(editor, start, end, EDITOR_INDENT, start + EDITOR_INDENT.length, start + EDITOR_INDENT.length);
    return;
  }
  const value = editor.value;
  const blockStart = value.lastIndexOf("\n", start - 1) + 1;
  const blockEnd = lineEndForSelection(value, end);
  const block = value.slice(blockStart, blockEnd);
  const lines = block.split("\n");
  const replacement = lines.map((line) => EDITOR_INDENT + line).join("\n");
  replaceEditorRange(
    editor,
    blockStart,
    blockEnd,
    replacement,
    start + EDITOR_INDENT.length,
    end + EDITOR_INDENT.length * lines.length,
  );
}

function unindentSelection(editor) {
  const value = editor.value;
  const start = editor.selectionStart;
  const end = editor.selectionEnd;
  const blockStart = value.lastIndexOf("\n", start - 1) + 1;
  const blockEnd = lineEndForSelection(value, end);
  const lines = value.slice(blockStart, blockEnd).split("\n");
  let removedBeforeStart = 0;
  let removedTotal = 0;
  let cursor = blockStart;
  const replacement = lines.map((line) => {
    let remove = 0;
    if (line.startsWith(EDITOR_INDENT)) remove = EDITOR_INDENT.length;
    else if (line.startsWith("	")) remove = 1;
    if (cursor + remove <= start) removedBeforeStart += remove;
    if (cursor < end) removedTotal += remove;
    cursor += line.length + 1;
    return line.slice(remove);
  }).join("\n");
  const nextStart = Math.max(blockStart, start - removedBeforeStart);
  const nextEnd = Math.max(nextStart, end - removedTotal);
  replaceEditorRange(editor, blockStart, blockEnd, replacement, nextStart, nextEnd);
}

function insertAutoIndent(editor) {
  const cursor = editor.selectionStart;
  const value = editor.value;
  const lineStart = value.lastIndexOf("\n", cursor - 1) + 1;
  const beforeCursor = value.slice(lineStart, cursor);
  const baseIndent = beforeCursor.match(/^ */)?.[0] || "";
  const extraIndent = beforeCursor.trimEnd().endsWith(":") ? EDITOR_INDENT : "";
  const insertion = "\n" + baseIndent + extraIndent;
  replaceEditorRange(editor, editor.selectionStart, editor.selectionEnd, insertion, cursor + insertion.length, cursor + insertion.length);
}

function shouldSmartOutdent(editor) {
  const cursor = editor.selectionStart;
  if (cursor < EDITOR_INDENT.length) return false;
  const lineStart = editor.value.lastIndexOf("\n", cursor - 1) + 1;
  const leading = editor.value.slice(lineStart, cursor);
  return leading.trim() === "" && editor.value.slice(cursor - EDITOR_INDENT.length, cursor) === EDITOR_INDENT;
}

function lineEndForSelection(value, end) {
  if (end > 0 && value[end - 1] === "\n") return end - 1;
  const nextNewline = value.indexOf("\n", end);
  return nextNewline === -1 ? value.length : nextNewline;
}

function replaceEditorRange(editor, start, end, text, nextStart, nextEnd) {
  editor.setRangeText(text, start, end, "preserve");
  editor.selectionStart = nextStart;
  editor.selectionEnd = nextEnd;
  editor.dispatchEvent(new Event("input", { bubbles: true }));
}

function updateEditorDecorations(editor, lineNumbers, highlightLayer, language) {
  updateLineNumbers(editor, lineNumbers);
  updateSyntaxHighlight(editor, highlightLayer, language);
  syncEditorScroll(editor, lineNumbers, highlightLayer);
}

function updateLineNumbers(editor, lineNumbers) {
  if (!lineNumbers) return;
  const lineCount = Math.max(1, editor.value.split("\n").length);
  let numbers = "";
  for (let line = 1; line <= lineCount; line += 1) numbers += line + "\n";
  lineNumbers.textContent = numbers;
}

function updateSyntaxHighlight(editor, highlightLayer, language) {
  if (!highlightLayer) return;
  const html = language === "json" ? highlightJson(editor.value) : highlightPython(editor.value);
  highlightLayer.innerHTML = html.endsWith("\n") ? html + " " : html || " ";
}

function syncEditorScroll(editor, lineNumbers, highlightLayer) {
  if (lineNumbers) lineNumbers.scrollTop = editor.scrollTop;
  if (highlightLayer) {
    highlightLayer.scrollTop = editor.scrollTop;
    highlightLayer.scrollLeft = editor.scrollLeft;
  }
}

function getEditorSnapshot(editor) {
  return state.editorSnapshots.get(editor) || { value: editor.value, at: Date.now() };
}

function setEditorSnapshot(editor, at = Date.now()) {
  state.editorSnapshots.set(editor, { value: editor.value, at });
  state.lastEditorValue = editor.value;
  state.lastEditAt = at;
}

const PYTHON_KEYWORDS = new Set([
  "False", "None", "True", "and", "as", "assert", "async", "await", "break", "class", "continue", "def", "del", "elif", "else", "except", "finally", "for", "from", "global", "if", "import", "in", "is", "lambda", "nonlocal", "not", "or", "pass", "raise", "return", "try", "while", "with", "yield",
]);
const PYTHON_BUILTINS = new Set([
  "abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "print", "range", "round", "set", "str", "sum", "tuple", "move_right", "move_left", "move_up", "move_down", "collect", "say", "at_goal", "on_gem", "get_energy", "get_score", "gem_value", "card_at", "get_route", "get_targets", "get_position",
]);

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

function highlightJson(source) {
  let out = "";
  let index = 0;
  while (index < source.length) {
    const ch = source[index];
    const rest = source.slice(index);
    if (ch === '"') {
      const token = readQuoted(source, index, '"');
      const nextIndex = index + token.length;
      const afterString = source.slice(nextIndex).match(/^\s*/)?.[0] || "";
      const isKey = source[nextIndex + afterString.length] === ":";
      out += isKey ? `<span class="tok-json-key">${escapeHtml(token)}</span>` : span("string", token);
      index += token.length;
    } else if (rest.startsWith("true") && !/[A-Za-z0-9_]/.test(source[index + 4] || "")) {
      out += span("bool", "true");
      index += 4;
    } else if (rest.startsWith("false") && !/[A-Za-z0-9_]/.test(source[index + 5] || "")) {
      out += span("bool", "false");
      index += 5;
    } else if (rest.startsWith("null") && !/[A-Za-z0-9_]/.test(source[index + 4] || "")) {
      out += span("null", "null");
      index += 4;
    } else if (/[-0-9]/.test(ch)) {
      const match = rest.match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/);
      if (match) {
        out += span("number", match[0]);
        index += match[0].length;
      } else {
        out += escapeHtml(ch);
        index += 1;
      }
    } else if (/[,:{}[\]]/.test(ch)) {
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

function span(kind, text) {
  return `<span class="tok-${kind}">${escapeHtml(text)}</span>`;
}

function blockClipboard(event, type, assignmentIdFn) {
  event.preventDefault();
  const editor = event.currentTarget;
  recordBehavior(type, 0, 0, editor.value.length, { assignment_id: assignmentIdFn() });
  showToast("Copy and paste are disabled in code editors.");
}

function recordBehavior(eventType, insertedLen, deletedLen, codeLen, metadata) {
  const assignmentId = metadata.assignment_id || state.currentAssignment?.id || "";
  state.behavior.push({
    assignment_id: assignmentId,
    event_type: eventType,
    inserted_len: insertedLen,
    deleted_len: deletedLen,
    code_len: codeLen,
    dt_ms: Number(metadata.input_ms || 0),
    metadata,
  });
  els.telemetryState.textContent = `${state.behavior.length} events queued`;
  if (state.behavior.length >= 40) flushBehavior(false);
}

async function flushBehavior(useBeacon) {
  if (!state.user || !state.behavior.length) return;
  const events = state.behavior.splice(0, state.behavior.length);
  els.telemetryState.textContent = "Typing log syncing";
  const payload = JSON.stringify({ events });
  try {
    if (useBeacon && navigator.sendBeacon) {
      navigator.sendBeacon("/api/behavior/log", new Blob([payload], { type: "application/json" }));
    } else {
      await fetch("/api/behavior/log", { method: "POST", headers: { "Content-Type": "application/json" }, body: payload, keepalive: true });
    }
    els.telemetryState.textContent = "Typing log synced";
  } catch (_error) {
    state.behavior.unshift(...events);
    els.telemetryState.textContent = "Typing log pending";
  }
}

function diffStats(before, after) {
  let start = 0;
  while (start < before.length && start < after.length && before[start] === after[start]) start += 1;
  let endBefore = before.length - 1;
  let endAfter = after.length - 1;
  while (endBefore >= start && endAfter >= start && before[endBefore] === after[endAfter]) {
    endBefore -= 1;
    endAfter -= 1;
  }
  return { inserted: Math.max(0, endAfter - start + 1), deleted: Math.max(0, endBefore - start + 1) };
}

function keyClass(key) {
  if (key.length === 1 && /[a-z]/i.test(key)) return "letter";
  if (key.length === 1 && /[0-9]/.test(key)) return "number";
  if (key.length === 1) return "symbol";
  if (["Backspace", "Delete", "Enter", "Tab", "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(key)) return key;
  return "control";
}

function setEditorValue(editor, value) {
  state.suppressInput = true;
  editor.value = value;
  setEditorSnapshot(editor);
  const decoration = decorationForEditor(editor);
  updateEditorDecorations(editor, decoration.lineNumbers, decoration.highlightLayer, decoration.language);
  state.suppressInput = false;
}

function decorationForEditor(editor) {
  if (editor === els.missionEditor) return { lineNumbers: els.missionLineNumbers, highlightLayer: els.missionHighlight, language: "python" };
  if (editor === els.codeEditor) return { lineNumbers: els.codeLineNumbers, highlightLayer: els.codeHighlight, language: "python" };
  if (editor === els.testEditor) return { lineNumbers: els.testLineNumbers, highlightLayer: els.testHighlight, language: "json" };
  return { lineNumbers: null, highlightLayer: null, language: "python" };
}

async function loadStudio() {
  updateStudioLock();
  if (!canUseStudio()) return;
  if (state.templates.length) return;
  const data = await apiGet("/api/templates");
  state.templates = data.templates || [];
  renderTemplateButtons();
  await loadTemplate("adventure");
}

function canUseStudio() {
  return state.user && (state.user.can_use_studio || state.user.role === "admin");
}

function updateStudioLock() {
  const open = canUseStudio();
  els.studioLocked.classList.toggle("hidden", open);
  els.studioWorkspace.classList.toggle("hidden", !open);
}

function renderTemplateButtons() {
  els.templateButtons.innerHTML = "";
  for (const template of state.templates) {
    const button = document.createElement("button");
    button.type = "button";
    button.dataset.template = template.id;
    button.innerHTML = `<strong>${escapeHtml(template.name)}</strong><br><span>${escapeHtml(template.tagline)}</span>`;
    button.addEventListener("click", () => loadTemplate(template.id));
    els.templateButtons.appendChild(button);
  }
}

async function loadTemplate(templateId) {
  const template = await apiGet(`/api/templates/${encodeURIComponent(templateId)}`);
  state.templateId = template.id;
  state.actionHistory = [];
  els.projectTitle.value = template.name === "Adventure Game" ? "Campus Cat Rescue" : template.name;
  els.projectCreator.value = state.user.display_name;
  els.projectDescription.value = template.tagline;
  els.specEditor.value = template.spec_prompt;
  setEditorValue(els.codeEditor, template.starter_code);
  setEditorValue(els.testEditor, template.starter_tests);
  document.querySelectorAll("[data-template]").forEach((button) => button.classList.toggle("is-active", button.dataset.template === template.id));
  setProjectStatus("Ready", "");
}

async function runProject(keepHistory) {
  if (!keepHistory) state.actionHistory = [];
  setBusy(true);
  try {
    const result = await apiPost("/api/run", { code: els.codeEditor.value, actions: state.actionHistory });
    renderProjectRun(result);
  } catch (error) {
    setProjectStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function resetProject() {
  state.actionHistory = [];
  runProject(true);
}

async function takeProjectAction(actionId) {
  state.actionHistory.push(actionId);
  await runProject(true);
}

function renderProjectRun(result) {
  if (!result.ok) {
    setProjectStatus(result.error || "Execution failed", "error");
    return;
  }
  els.playTitle.textContent = result.title || "Project Preview";
  els.scoreBadge.textContent = `Score ${String(result.score ?? 0)}`;
  els.stateText.textContent = result.state_text || "";
  els.stateJson.textContent = JSON.stringify(result.state || {}, null, 2);
  els.consoleOutput.textContent = result.stdout || "";
  els.actionButtons.innerHTML = "";
  setProjectStatus(result.won ? "Won" : result.lost ? "Ended" : "Playable", result.won || result.lost ? "" : "success");
  for (const action of result.actions || []) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label || action.id;
    button.addEventListener("click", () => takeProjectAction(action.id));
    els.actionButtons.appendChild(button);
  }
}

async function runProjectTests() {
  setBusy(true);
  try {
    const result = await apiPost("/api/test", { code: els.codeEditor.value, tests: els.testEditor.value });
    els.testResults.innerHTML = "";
    if (!result.ok) {
      setProjectStatus(result.error || "Tests failed", "error");
      return;
    }
    const summary = result.summary || { passed: 0, total: 0 };
    setProjectStatus(`${summary.passed}/${summary.total} tests passed`, summary.passed === summary.total ? "success" : "error");
    renderProjectChecks(result.results || []);
  } finally {
    setBusy(false);
  }
}

function renderProjectChecks(items) {
  els.testResults.innerHTML = "";
  for (const item of items) {
    const row = document.createElement("div");
    row.className = `check-item ${item.passed ? "pass" : "fail"}`;
    row.innerHTML = `<strong>${item.passed ? "Pass" : "Fix"}: ${escapeHtml(item.name)}</strong><p>${escapeHtml(item.details || "")}</p>`;
    els.testResults.appendChild(row);
  }
}

async function askAI(mode) {
  setBusy(true);
  try {
    const result = await apiPost("/api/ai/draft", {
      mode,
      template_id: state.templateId,
      specification: els.specEditor.value,
      code: els.codeEditor.value,
      tests: els.testEditor.value,
    });
    if (mode === "tests") {
      setEditorValue(els.testEditor, result.content);
      switchProjectEditor("tests");
    } else if (mode === "feedback") {
      appendAIRecord("AI feedback", result.content);
    } else {
      setEditorValue(els.codeEditor, result.content);
      switchProjectEditor("code");
    }
    if (mode !== "feedback") appendAIRecord(`AI ${mode}`, result.raw || result.content);
    setProjectStatus("AI response received", "success");
  } catch (error) {
    setProjectStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

function appendAIRecord(title, content) {
  const block = `[${new Date().toISOString()}] ${title}\n${content}\n`;
  els.aiRecord.value = els.aiRecord.value ? `${els.aiRecord.value}\n${block}` : block;
}

async function publishProject() {
  setBusy(true);
  try {
    const project = await apiPost("/api/projects", {
      title: els.projectTitle.value,
      creator: els.projectCreator.value,
      description: els.projectDescription.value,
      template_id: state.templateId,
      code: els.codeEditor.value,
      tests: els.testEditor.value,
      specification: els.specEditor.value,
      ai_record: els.aiRecord.value,
    });
    await loadProjects();
    showToast(`${location.origin}/#/project/${project.slug}`);
  } finally {
    setBusy(false);
  }
}

function switchProjectEditor(editor) {
  document.querySelectorAll(".editor-tab").forEach((button) => button.classList.toggle("is-active", button.dataset.editor === editor));
  els.codeEditorShell.classList.toggle("is-active", editor === "code");
  els.testEditorShell.classList.toggle("is-active", editor === "tests");
  updateEditorDecorations(els.codeEditor, els.codeLineNumbers, els.codeHighlight, "python");
  updateEditorDecorations(els.testEditor, els.testLineNumbers, els.testHighlight, "json");
}

function setProjectStatus(message, kind) {
  els.statusBanner.textContent = message;
  els.statusBanner.className = `status-banner ${kind || ""}`;
}

async function loadProjects() {
  if (!state.user) return;
  const data = await apiGet("/api/projects");
  els.projectGrid.innerHTML = "";
  for (const project of data.projects || []) {
    const card = document.createElement("article");
    card.className = "project-card";
    card.innerHTML = `<div class="meta">${escapeHtml(project.template_id)}</div><h3>${escapeHtml(project.title)}</h3><p>${escapeHtml(project.description)}</p><p>Created by ${escapeHtml(project.creator)}</p><button type="button">Open</button>`;
    card.querySelector("button").addEventListener("click", () => openProject(project.slug));
    els.projectGrid.appendChild(card);
  }
  if (!els.projectGrid.children.length) els.projectGrid.textContent = "No projects published yet.";
}

async function openProject(slug) {
  const project = await apiGet(`/api/projects/${encodeURIComponent(slug)}`);
  if (!canUseStudio()) {
    showToast("Project Studio is locked.");
    return;
  }
  await loadStudio();
  state.templateId = project.template_id;
  state.actionHistory = [];
  els.projectTitle.value = project.title || "";
  els.projectCreator.value = project.creator || "";
  els.projectDescription.value = project.description || "";
  els.specEditor.value = project.specification || "";
  els.aiRecord.value = project.ai_record || "";
  setEditorValue(els.codeEditor, project.code || "");
  setEditorValue(els.testEditor, project.tests || "[]");
  switchView("studio");
  await runProject(true);
}

async function loadAdmin() {
  if (state.user?.role !== "admin") return;
  const data = await apiGet("/api/admin/overview");
  renderAdmin(data);
}

function renderAdmin(data) {
  const assignmentOptions = state.assignments.map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.order)}. ${escapeHtml(item.title)}</option>`).join("");
  els.adminUsersTable.innerHTML = `<thead><tr><th>User</th><th>Role</th><th>Done</th><th>Runs</th><th>Paste</th><th>Large Inserts</th><th>Risk</th><th>Unlock</th><th>Password</th></tr></thead><tbody></tbody>`;
  const tbody = els.adminUsersTable.querySelector("tbody");
  for (const user of data.users || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${escapeHtml(user.display_name)}<br><span class="muted">${escapeHtml(user.username)}</span></td><td>${escapeHtml(user.role)}</td><td>${user.completed_count}/${data.assignment_count}</td><td>${user.run_count || 0}</td><td>${user.paste_attempts || 0}</td><td>${user.large_insertions || 0}</td><td>${user.risk_score || 0}</td><td><select>${assignmentOptions}</select><button type="button">Unlock</button></td><td><button type="button">Reset</button></td>`;
    const unlockButton = tr.querySelectorAll("button")[0];
    const resetButton = tr.querySelectorAll("button")[1];
    unlockButton.addEventListener("click", async () => {
      const assignmentId = tr.querySelector("select").value;
      await apiPost("/api/admin/unlock", { user_id: user.id, assignment_id: assignmentId });
      showToast("Assignment unlocked.");
      await loadAdmin();
    });
    resetButton.addEventListener("click", async () => {
      const password = prompt("Temporary password");
      if (!password) return;
      await apiPost("/api/admin/reset-password", { user_id: user.id, password });
      showToast("Password reset.");
    });
    tbody.appendChild(tr);
  }

  els.adminSubmissionsTable.innerHTML = `<thead><tr><th>ID</th><th>User</th><th>Assignment</th><th>Passed</th><th>Time</th></tr></thead><tbody></tbody>`;
  const submissionBody = els.adminSubmissionsTable.querySelector("tbody");
  for (const submission of data.submissions || []) {
    const tr = document.createElement("tr");
    tr.innerHTML = `<td>${submission.id}</td><td>${escapeHtml(submission.username)}</td><td>${escapeHtml(submission.assignment_id)}</td><td>${submission.passed ? "yes" : "no"}</td><td>${escapeHtml(submission.created_at)}</td>`;
    submissionBody.appendChild(tr);
  }
}

async function adminCreateUser(event) {
  event.preventDefault();
  await apiPost("/api/admin/users", {
    display_name: document.querySelector("#adminDisplayName").value,
    username: document.querySelector("#adminUsername").value,
    password: document.querySelector("#adminPassword").value,
    role: document.querySelector("#adminRole").value,
  });
  event.target.reset();
  showToast("User created.");
  await loadAdmin();
}

async function switchView(view) {
  if (view === "studio") await loadStudio();
  if (view === "admin") await loadAdmin();
  if (view === "showcase") await loadProjects();
  if (view === "pacman" && els.pacmanFrame && !els.pacmanFrame.src) els.pacmanFrame.src = els.pacmanFrame.dataset.src;
  document.querySelectorAll(".nav-tab").forEach((button) => button.classList.toggle("is-active", button.dataset.view === view));
  document.querySelectorAll(".view").forEach((panel) => panel.classList.toggle("is-active", panel.id === `${view}View`));
}

function setBusy(busy) {
  state.busy = busy;
  document.querySelectorAll("button").forEach((button) => { button.disabled = busy; });
}

async function apiGet(path) {
  const response = await fetch(path, { credentials: "same-origin" });
  return parseResponse(response);
}

async function apiPost(path, body) {
  const response = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

async function parseResponse(response) {
  const data = await response.json();
  if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
  return data;
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("is-visible");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => els.toast.classList.remove("is-visible"), 4200);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
