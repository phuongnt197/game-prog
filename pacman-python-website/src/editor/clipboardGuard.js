const CLIPBOARD_SHORTCUT_KEYS = new Set(["c", "v", "x"]);
const CLIPBOARD_INPUT_TYPES = new Set(["insertFromPaste", "insertFromDrop"]);

export const COPY_PASTE_DISABLED_MESSAGE = "Copy and paste are disabled in student assessment editors.";
export const CLIPBOARD_NOTICE_DURATION_MS = 5000;

export function scheduleClipboardNoticeDismissal(setMessage, delay = CLIPBOARD_NOTICE_DURATION_MS) {
  const timer = setTimeout(() => {
    setMessage((current) => current === COPY_PASTE_DISABLED_MESSAGE ? "" : current);
  }, delay);
  return () => clearTimeout(timer);
}

export function isClipboardShortcut(event) {
  return Boolean((event.ctrlKey || event.metaKey) && CLIPBOARD_SHORTCUT_KEYS.has(event.key?.toLowerCase()));
}

export function isClipboardInsertion(event) {
  return CLIPBOARD_INPUT_TYPES.has(event.inputType || event.nativeEvent?.inputType);
}

export function createClipboardGuard(onBlocked) {
  const block = (event) => {
    event.preventDefault();
    onBlocked?.(event);
    return true;
  };

  return {
    block,
    handleKeyDown(event) {
      return isClipboardShortcut(event) ? block(event) : false;
    },
    handleBeforeInput(event) {
      return isClipboardInsertion(event) ? block(event) : false;
    },
  };
}
