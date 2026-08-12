const KEYWORDS = new Set("False None True and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield".split(" "));
const BUILTINS = new Set("abs all any bool dict enumerate float int len list max min print range round set str sum tuple manhattan_distance nearest_food".split(" "));

const escapeHtml = (value) => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
const span = (kind, value) => `<span class="tok-${kind}">${escapeHtml(value)}</span>`;

function readQuoted(source, start, quote, triple = false) {
  const marker = triple ? quote.repeat(3) : quote;
  let index = start + marker.length;
  while (index < source.length) {
    if (!triple && source[index] === "\\") index += 2;
    else if (source.slice(index, index + marker.length) === marker) return source.slice(start, index + marker.length);
    else index += 1;
  }
  return source.slice(start);
}

export function highlightPython(source) {
  let html = ""; let index = 0;
  while (index < source.length) {
    const rest = source.slice(index); const char = source[index];
    let token; let kind;
    if (char === "#") { const end = source.indexOf("\n", index); token = end < 0 ? rest : source.slice(index, end); kind = "comment"; }
    else if ((char === "'" || char === '"') && source.slice(index, index + 3) === char.repeat(3)) { token = readQuoted(source, index, char, true); kind = "string"; }
    else if (char === "'" || char === '"') { token = readQuoted(source, index, char); kind = "string"; }
    else if (/\d/.test(char)) { token = rest.match(/^\d+(?:\.\d+)?/)[0]; kind = "number"; }
    else if (/[A-Za-z_]/.test(char)) { token = rest.match(/^[A-Za-z_]\w*/)[0]; kind = KEYWORDS.has(token) ? "keyword" : BUILTINS.has(token) ? "builtin" : null; }
    else if (char === "@" && /[A-Za-z_]/.test(source[index + 1] || "")) { token = rest.match(/^@[A-Za-z_]\w*/)[0]; kind = "decorator"; }
    else { token = char; kind = /[+\-*\/%=<>!&|^~:.,()[\]{}]/.test(char) ? "operator" : null; }
    html += kind ? span(kind, token) : escapeHtml(token); index += token.length;
  }
  return html;
}
