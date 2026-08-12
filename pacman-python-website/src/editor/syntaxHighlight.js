import { highlightPython } from "./pythonHighlight";

const escapeHtml = (value) => String(value)
  .replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const token = (kind, value) => `<span class="tok-${kind}">${escapeHtml(value)}</span>`;

export function highlightJson(source) {
  let html = ""; let index = 0;
  while (index < source.length) {
    const rest = source.slice(index); const char = source[index];
    if (char === '"') {
      let end = index + 1;
      while (end < source.length) {
        if (source[end] === "\\") end += 2;
        else if (source[end] === '"') { end += 1; break; }
        else end += 1;
      }
      const value = source.slice(index, end); const after = source.slice(end).match(/^\s*:/);
      html += token(after ? "json-key" : "string", value); index = end;
    } else if (rest.match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/)) {
      const value = rest.match(/^-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?/)[0]; html += token("number", value); index += value.length;
    } else if (rest.match(/^(true|false)\b/)) {
      const value = rest.match(/^(true|false)\b/)[0]; html += token("bool", value); index += value.length;
    } else if (rest.match(/^null\b/)) {
      html += token("null", "null"); index += 4;
    } else if (/[,:{}\[\]]/.test(char)) {
      html += token("operator", char); index += 1;
    } else { html += escapeHtml(char); index += 1; }
  }
  return html;
}

export const highlightCode = (source, language = "python") => language === "json" ? highlightJson(source) : highlightPython(source);
