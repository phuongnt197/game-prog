export const EDITOR_HISTORY_LIMIT = 200;

const clamp = (value, minimum, maximum) => Math.min(Math.max(value, minimum), maximum);

export function createEditorSnapshot(value, selectionStart = 0, selectionEnd = selectionStart) {
  const text = String(value ?? "");
  const start = clamp(Number(selectionStart) || 0, 0, text.length);
  const end = clamp(Number(selectionEnd) || 0, start, text.length);
  return { value: text, selectionStart: start, selectionEnd: end };
}

export function inferEditorSnapshot(previousValue, nextValue, nextSelectionStart = 0) {
  const previous = String(previousValue ?? "");
  const next = String(nextValue ?? "");
  let prefix = 0;
  while (prefix < previous.length && prefix < next.length && previous[prefix] === next[prefix]) prefix += 1;

  let suffix = 0;
  while (
    suffix < previous.length - prefix
    && suffix < next.length - prefix
    && previous[previous.length - suffix - 1] === next[next.length - suffix - 1]
  ) suffix += 1;

  const replacedEnd = previous.length - suffix;
  return createEditorSnapshot(previous, prefix, Math.max(prefix, replacedEnd));
}

export function editorHistoryGroup(inputType = "") {
  if (["insertText", "insertCompositionText"].includes(inputType)) return "insert";
  if (inputType === "deleteContentBackward") return "delete-backward";
  if (inputType === "deleteContentForward") return "delete-forward";
  return null;
}

export function editorHistoryAction(event) {
  if (!(event.ctrlKey || event.metaKey) || event.altKey) return null;
  const key = event.key?.toLowerCase();
  if (key === "z") return event.shiftKey ? "redo" : "undo";
  return key === "y" ? "redo" : null;
}

const sameSelection = (left, right) => (
  left.selectionStart === right.selectionStart && left.selectionEnd === right.selectionEnd
);

export function createEditorHistory(limit = EDITOR_HISTORY_LIMIT) {
  let undoStack = [];
  let redoStack = [];
  let lastEdit = null;

  const trim = (stack) => {
    if (stack.length > limit) stack.splice(0, stack.length - limit);
  };
  const breakGroup = () => { lastEdit = null; };

  return {
    record(before, after, group = null) {
      if (before.value === after.value) return;
      const continuesGroup = Boolean(
        group
        && lastEdit?.group === group
        && lastEdit.after.value === before.value
        && sameSelection(lastEdit.after, before)
      );
      if (!continuesGroup) {
        undoStack.push(before);
        trim(undoStack);
      }
      redoStack = [];
      lastEdit = { group, after };
    },
    undo(current) {
      const target = undoStack.pop();
      if (!target) return null;
      redoStack.push(current);
      trim(redoStack);
      breakGroup();
      return target;
    },
    redo(current) {
      const target = redoStack.pop();
      if (!target) return null;
      undoStack.push(current);
      trim(undoStack);
      breakGroup();
      return target;
    },
    reset() {
      undoStack = [];
      redoStack = [];
      breakGroup();
    },
    breakGroup,
    sizes() {
      return { undo: undoStack.length, redo: redoStack.length };
    },
  };
}
