import { useMemo, useRef } from "react";
import { COPY_PASTE_DISABLED_MESSAGE, createClipboardGuard } from "../editor/clipboardGuard";
import { createEditorHistory, createEditorSnapshot, editorHistoryAction, editorHistoryGroup, inferEditorSnapshot } from "../editor/editorHistory";
import { highlightCode } from "../editor/syntaxHighlight";

const INDENT = "    ";

const decorations = (value, language) => {
  const lines = Array.from({ length: Math.max(1, value.split("\n").length) }, (_, index) => index + 1).join("\n");
  const highlighted = highlightCode(value, language);
  return { lines, highlighted: highlighted.endsWith("\n") ? `${highlighted} ` : highlighted || " " };
};

export function SyntaxEditor({ value, onChange, language = "python", ariaLabel = "Code editor", minHeight = 260, disabled = false, preventClipboard = false, onBlockedClipboard, historyKey }) {
  const inputRef = useRef(null); const linesRef = useRef(null); const codeRef = useRef(null);
  const historyRef = useRef(null); const pendingInputRef = useRef(null); const expectedValueRef = useRef(value); const historyKeyRef = useRef(historyKey);
  if (!historyRef.current) historyRef.current = createEditorHistory();
  if (historyKeyRef.current !== historyKey || expectedValueRef.current !== value) {
    historyRef.current.reset();
    pendingInputRef.current = null;
    expectedValueRef.current = value;
    historyKeyRef.current = historyKey;
  }
  const { lines, highlighted } = useMemo(() => decorations(value, language), [value, language]);
  const clipboardGuard = preventClipboard ? createClipboardGuard(onBlockedClipboard) : null;
  const restoreSelection = ({ selectionStart, selectionEnd }) => {
    requestAnimationFrame(() => {
      inputRef.current?.focus();
      inputRef.current?.setSelectionRange(selectionStart, selectionEnd);
    });
  };
  const commit = (snapshot) => {
    expectedValueRef.current = snapshot.value;
    pendingInputRef.current = null;
    onChange(snapshot.value);
    restoreSelection(snapshot);
  };
  const replace = (start, end, text, nextStart, nextEnd = nextStart) => {
    const before = createEditorSnapshot(value, start, end);
    const after = createEditorSnapshot(value.slice(0, start) + text + value.slice(end), nextStart, nextEnd);
    historyRef.current.record(before, after);
    commit(after);
  };
  const moveThroughHistory = (action, target) => {
    const current = createEditorSnapshot(value, target.selectionStart, target.selectionEnd);
    const snapshot = historyRef.current[action](current);
    if (snapshot) commit(snapshot);
  };
  const keyDown = (event) => {
    if (clipboardGuard?.handleKeyDown(event)) return;
    const historyAction = editorHistoryAction(event);
    if (historyAction) {
      event.preventDefault();
      moveThroughHistory(historyAction, event.currentTarget);
      return;
    }
    const { selectionStart: start, selectionEnd: end } = event.currentTarget;
    if (event.key === "Tab") {
      event.preventDefault();
      if (start === end) {
        if (event.shiftKey) {
          const lineStart = value.lastIndexOf("\n", start - 1) + 1; const removable = value.slice(lineStart, start).match(/^( {1,4}|\t)/)?.[0] || "";
          replace(lineStart, lineStart + removable.length, "", Math.max(lineStart, start - removable.length));
        } else replace(start, end, INDENT, start + INDENT.length);
        return;
      }
      const blockStart = value.lastIndexOf("\n", start - 1) + 1; const nextBreak = value.indexOf("\n", end); const blockEnd = nextBreak < 0 ? value.length : nextBreak;
      const rows = value.slice(blockStart, blockEnd).split("\n");
      const replacement = rows.map((row) => event.shiftKey ? row.replace(/^( {1,4}|\t)/, "") : INDENT + row).join("\n");
      replace(blockStart, blockEnd, replacement, blockStart, blockStart + replacement.length);
    } else if (event.key === "Enter") {
      event.preventDefault(); const lineStart = value.lastIndexOf("\n", start - 1) + 1; const before = value.slice(lineStart, start); const base = before.match(/^\s*/)?.[0] || "";
      const extra = language === "python" ? (before.trimEnd().endsWith(":") ? INDENT : "") : (/[{\[]\s*$/.test(before) ? INDENT : "");
      const insertion = `\n${base}${extra}`; replace(start, end, insertion, start + insertion.length);
    }
  };
  const beforeInput = (event) => {
    if (clipboardGuard?.handleBeforeInput(event)) return;
    const inputType = event.inputType || event.nativeEvent?.inputType || "";
    if (["historyUndo", "historyRedo"].includes(inputType)) {
      event.preventDefault();
      moveThroughHistory(inputType === "historyUndo" ? "undo" : "redo", event.currentTarget);
      return;
    }
    pendingInputRef.current = {
      before: createEditorSnapshot(value, event.currentTarget.selectionStart, event.currentTarget.selectionEnd),
      group: editorHistoryGroup(inputType),
    };
  };
  const change = (event) => {
    const nextValue = event.currentTarget.value;
    const after = createEditorSnapshot(nextValue, event.currentTarget.selectionStart, event.currentTarget.selectionEnd);
    const pending = pendingInputRef.current;
    const before = pending?.before || inferEditorSnapshot(value, nextValue, event.currentTarget.selectionStart);
    historyRef.current.record(before, after, pending?.group);
    expectedValueRef.current = nextValue;
    pendingInputRef.current = null;
    onChange(nextValue);
  };
  const scroll = ({ currentTarget }) => { linesRef.current.scrollTop = currentTarget.scrollTop; codeRef.current.scrollTop = currentTarget.scrollTop; codeRef.current.scrollLeft = currentTarget.scrollLeft; };
  return <div className={`shared-syntax-editor ${disabled ? "is-disabled" : ""}`} style={{ minHeight }} data-clipboard-disabled={preventClipboard || undefined}>
    <pre ref={linesRef} className="shared-line-numbers" aria-hidden="true">{lines}</pre>
    <pre ref={codeRef} className="shared-syntax-layer" aria-hidden="true" dangerouslySetInnerHTML={{ __html: highlighted }} />
    <textarea ref={inputRef} className="shared-syntax-input" value={value} onChange={change} onKeyDown={keyDown} onBeforeInput={beforeInput} onScroll={scroll} disabled={disabled} onPaste={clipboardGuard?.block} onCopy={clipboardGuard?.block} onCut={clipboardGuard?.block} onDrop={clipboardGuard?.block} onDragStart={clipboardGuard?.block} onContextMenu={clipboardGuard?.block} spellCheck="false" autoComplete="off" autoCorrect="off" autoCapitalize="off" aria-label={ariaLabel} title={preventClipboard ? COPY_PASTE_DISABLED_MESSAGE : undefined} />
  </div>;
}

export function HighlightedCode({ code = "", language = "python", ariaLabel = "Code" }) {
  const { lines, highlighted } = useMemo(() => decorations(String(code), language), [code, language]);
  return <div className="shared-code-viewer" role="region" aria-label={ariaLabel} tabIndex="0">
    <pre className="shared-line-numbers" aria-hidden="true">{lines}</pre>
    <pre className="shared-viewer-code" dangerouslySetInnerHTML={{ __html: highlighted }} />
  </div>;
}
