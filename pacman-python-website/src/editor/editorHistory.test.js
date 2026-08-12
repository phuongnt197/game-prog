import { describe, expect, it } from "vitest";
import {
  createEditorHistory,
  createEditorSnapshot,
  editorHistoryAction,
  editorHistoryGroup,
  inferEditorSnapshot,
} from "./editorHistory";

const snapshot = (value, selectionStart = value.length, selectionEnd = selectionStart) => (
  createEditorSnapshot(value, selectionStart, selectionEnd)
);

describe("syntax editor history", () => {
  it("undoes and redoes edits across multiple lines with their selections", () => {
    const history = createEditorHistory();
    const first = snapshot("first");
    const newline = snapshot("first\n", 6);
    const second = snapshot("first\nsecond", 12);

    history.record(snapshot("", 0), first, "insert");
    history.record(first, newline);
    history.record(newline, second, "insert");

    expect(history.undo(second)).toEqual(newline);
    expect(history.undo(newline)).toEqual(first);
    expect(history.undo(first)).toEqual(snapshot("", 0));
    expect(history.redo(snapshot("", 0))).toEqual(first);
    expect(history.redo(first)).toEqual(newline);
    expect(history.redo(newline)).toEqual(second);
  });

  it("groups continuous typing but starts a new entry after the cursor moves", () => {
    const history = createEditorHistory();
    history.record(snapshot("", 0), snapshot("a"), "insert");
    history.record(snapshot("a"), snapshot("ab"), "insert");
    history.record(snapshot("ab", 0), snapshot("cab", 1), "insert");

    expect(history.sizes()).toEqual({ undo: 2, redo: 0 });
    expect(history.undo(snapshot("cab", 1))).toEqual(snapshot("ab", 0));
    expect(history.undo(snapshot("ab", 0))).toEqual(snapshot("", 0));
  });

  it("clears redo after a new edit and resets history for external source changes", () => {
    const history = createEditorHistory();
    history.record(snapshot("", 0), snapshot("one"));
    expect(history.undo(snapshot("one"))).toEqual(snapshot("", 0));
    history.record(snapshot("", 0), snapshot("two"));
    expect(history.redo(snapshot("two"))).toBeNull();
    history.reset();
    expect(history.sizes()).toEqual({ undo: 0, redo: 0 });
  });

  it("maps platform undo and redo shortcuts", () => {
    expect(editorHistoryAction({ ctrlKey: true, key: "z" })).toBe("undo");
    expect(editorHistoryAction({ metaKey: true, shiftKey: true, key: "Z" })).toBe("redo");
    expect(editorHistoryAction({ ctrlKey: true, key: "y" })).toBe("redo");
    expect(editorHistoryAction({ ctrlKey: true, altKey: true, key: "z" })).toBeNull();
    expect(editorHistoryAction({ key: "z" })).toBeNull();
  });

  it("groups only continuous text insertion and deletion input types", () => {
    expect(editorHistoryGroup("insertText")).toBe("insert");
    expect(editorHistoryGroup("deleteContentBackward")).toBe("delete-backward");
    expect(editorHistoryGroup("insertFromPaste")).toBeNull();
  });

  it("infers the selection replaced when before-input metadata is unavailable", () => {
    expect(inferEditorSnapshot("hello world", "hello Codex", 11)).toEqual(snapshot("hello world", 6, 11));
    expect(inferEditorSnapshot("abc", "abxc", 3)).toEqual(snapshot("abc", 2, 2));
    expect(inferEditorSnapshot("abc", "xabc", 1)).toEqual(snapshot("abc", 0, 0));
  });
});
