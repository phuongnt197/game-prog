import { useMemo, useRef } from "react";
import { highlightPython } from "../editor/pythonHighlight";

const INDENT = "    ";

export function CodeEditor({ code, onChange, onBlockedClipboard }) {
  const editorRef = useRef(null); const numbersRef = useRef(null); const highlightRef = useRef(null);
  const lines = useMemo(() => Array.from({ length: Math.max(1, code.split("\n").length) }, (_, i) => i + 1).join("\n"), [code]);
  const highlighted = useMemo(() => { const html = highlightPython(code); return html.endsWith("\n") ? `${html} ` : html || " "; }, [code]);

  const replace = (start, end, text, selectionStart, selectionEnd = selectionStart) => {
    onChange(code.slice(0, start) + text + code.slice(end));
    requestAnimationFrame(() => { editorRef.current.focus(); editorRef.current.setSelectionRange(selectionStart, selectionEnd); });
  };
  const onKeyDown = (event) => {
    const editor = editorRef.current; const { selectionStart: start, selectionEnd: end } = editor;
    if ((event.ctrlKey || event.metaKey) && ["v", "c", "x"].includes(event.key.toLowerCase())) return onBlockedClipboard(event);
    if (event.key === "Tab") {
      event.preventDefault();
      if (start === end) return replace(start, end, event.shiftKey ? "" : INDENT, event.shiftKey ? start : start + 4);
      const blockStart = code.lastIndexOf("\n", start - 1) + 1;
      const blockEnd = code.indexOf("\n", end) < 0 ? code.length : code.indexOf("\n", end);
      const rows = code.slice(blockStart, blockEnd).split("\n");
      const replacement = rows.map((row) => event.shiftKey ? row.replace(/^( {1,4}|\t)/, "") : INDENT + row).join("\n");
      return replace(blockStart, blockEnd, replacement, blockStart, blockStart + replacement.length);
    }
    if (event.key === "Enter") {
      event.preventDefault(); const lineStart = code.lastIndexOf("\n", start - 1) + 1;
      const before = code.slice(lineStart, start); const indent = before.match(/^ */)?.[0] || "";
      const insertion = `\n${indent}${before.trimEnd().endsWith(":") ? INDENT : ""}`;
      replace(start, end, insertion, start + insertion.length);
    }
  };
  const syncScroll = ({ currentTarget }) => {
    numbersRef.current.scrollTop = currentTarget.scrollTop;
    highlightRef.current.scrollTop = currentTarget.scrollTop; highlightRef.current.scrollLeft = currentTarget.scrollLeft;
  };
  return <div className="editor-shell">
    <pre ref={numbersRef} className="line-numbers" aria-hidden="true">{lines}</pre>
    <pre ref={highlightRef} className="syntax-layer" aria-hidden="true" dangerouslySetInnerHTML={{ __html: highlighted }} />
    <textarea id="codeEditor" ref={editorRef} value={code} onChange={(e) => onChange(e.target.value)} onScroll={syncScroll}
      onKeyDown={onKeyDown} onPaste={onBlockedClipboard} onCopy={onBlockedClipboard} onCut={onBlockedClipboard}
      onDrop={onBlockedClipboard} onContextMenu={(e) => e.preventDefault()} spellCheck="false" autoComplete="off"
      autoCorrect="off" autoCapitalize="off" aria-label="Pacman Python editor" />
  </div>;
}
