import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";
import { SyntaxEditor } from "../components/SyntaxCode";
import {
  CLIPBOARD_NOTICE_DURATION_MS,
  COPY_PASTE_DISABLED_MESSAGE,
  createClipboardGuard,
  isClipboardInsertion,
  isClipboardShortcut,
  scheduleClipboardNoticeDismissal,
} from "./clipboardGuard";

const event = (overrides = {}) => ({
  preventDefault: vi.fn(),
  ...overrides,
});

describe("assessment editor clipboard guard", () => {
  it("recognizes copy, cut, and paste keyboard shortcuts on every platform", () => {
    expect(isClipboardShortcut(event({ ctrlKey: true, key: "c" }))).toBe(true);
    expect(isClipboardShortcut(event({ metaKey: true, key: "V" }))).toBe(true);
    expect(isClipboardShortcut(event({ ctrlKey: true, key: "x" }))).toBe(true);
    expect(isClipboardShortcut(event({ ctrlKey: true, key: "a" }))).toBe(false);
    expect(isClipboardShortcut(event({ key: "v" }))).toBe(false);
  });

  it("recognizes paste and drop before-input events", () => {
    expect(isClipboardInsertion(event({ inputType: "insertFromPaste" }))).toBe(true);
    expect(isClipboardInsertion(event({ nativeEvent: { inputType: "insertFromDrop" } }))).toBe(true);
    expect(isClipboardInsertion(event({ inputType: "insertText" }))).toBe(false);
  });

  it("prevents clipboard events and reports blocked attempts", () => {
    const onBlocked = vi.fn();
    const guard = createClipboardGuard(onBlocked);
    const copyEvent = event();

    expect(guard.block(copyEvent)).toBe(true);
    expect(copyEvent.preventDefault).toHaveBeenCalledOnce();
    expect(onBlocked).toHaveBeenCalledWith(copyEvent);
  });

  it("prevents clipboard shortcuts before editor key handling", () => {
    const guard = createClipboardGuard();
    const pasteEvent = event({ ctrlKey: true, key: "v" });

    expect(guard.handleKeyDown(pasteEvent)).toBe(true);
    expect(pasteEvent.preventDefault).toHaveBeenCalledOnce();
  });

  it("leaves ordinary editor keyboard and text input alone", () => {
    const guard = createClipboardGuard();
    const keyEvent = event({ ctrlKey: true, key: "z" });
    const inputEvent = event({ inputType: "insertText" });

    expect(guard.handleKeyDown(keyEvent)).toBe(false);
    expect(guard.handleBeforeInput(inputEvent)).toBe(false);
    expect(keyEvent.preventDefault).not.toHaveBeenCalled();
    expect(inputEvent.preventDefault).not.toHaveBeenCalled();
  });

  it("keeps clipboard prevention opt-in for student editors", () => {
    const protectedEditor = renderToStaticMarkup(createElement(SyntaxEditor, {
      value: "print('student')",
      onChange: () => {},
      preventClipboard: true,
    }));
    const unrestrictedEditor = renderToStaticMarkup(createElement(SyntaxEditor, {
      value: "print('teacher')",
      onChange: () => {},
    }));

    expect(protectedEditor).toContain('data-clipboard-disabled="true"');
    expect(protectedEditor).toContain("Copy and paste are disabled");
    expect(unrestrictedEditor).not.toContain("data-clipboard-disabled");
    expect(unrestrictedEditor).not.toContain("Copy and paste are disabled");
  });

  it("dismisses only the clipboard notice after five seconds", () => {
    vi.useFakeTimers();
    try {
      const setMessage = vi.fn();
      scheduleClipboardNoticeDismissal(setMessage);

      vi.advanceTimersByTime(CLIPBOARD_NOTICE_DURATION_MS - 1);
      expect(setMessage).not.toHaveBeenCalled();
      vi.advanceTimersByTime(1);
      expect(setMessage).toHaveBeenCalledOnce();

      const updateMessage = setMessage.mock.calls[0][0];
      expect(updateMessage(COPY_PASTE_DISABLED_MESSAGE)).toBe("");
      expect(updateMessage("A newer server error")).toBe("A newer server error");
    } finally {
      vi.useRealTimers();
    }
  });

  it("cancels a pending dismissal when its page unmounts or message changes", () => {
    vi.useFakeTimers();
    try {
      const setMessage = vi.fn();
      const cancel = scheduleClipboardNoticeDismissal(setMessage);
      cancel();
      vi.advanceTimersByTime(CLIPBOARD_NOTICE_DURATION_MS);
      expect(setMessage).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
