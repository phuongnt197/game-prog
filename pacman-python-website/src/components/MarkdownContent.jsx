import { HighlightedCode } from "./SyntaxCode";


export function MarkdownContent({ content = "" }) {
  const blocks = parseBlocks(String(content));
  return <div className="markdown-content">{blocks.map((block, index) => renderBlock(block, index))}</div>;
}


function parseBlocks(source) {
  const lines = source.replaceAll("\r\n", "\n").split("\n");
  const blocks = [];
  let index = 0;
  while (index < lines.length) {
    const line = lines[index];
    if (!line.trim()) { index += 1; continue; }

    const fence = line.match(/^\s*```([^`]*)$/);
    if (fence) {
      const code = [];
      index += 1;
      while (index < lines.length && !/^\s*```\s*$/.test(lines[index])) {
        code.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) index += 1;
      blocks.push({ type: "code", language: fence[1].trim().toLowerCase(), content: code.join("\n") });
      continue;
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      blocks.push({ type: "heading", level: heading[1].length, content: heading[2] });
      index += 1;
      continue;
    }
    if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
      blocks.push({ type: "rule" });
      index += 1;
      continue;
    }
    if (/^\s*>/.test(line)) {
      const quoted = [];
      while (index < lines.length && /^\s*>/.test(lines[index])) {
        quoted.push(lines[index].replace(/^\s*>\s?/, ""));
        index += 1;
      }
      blocks.push({ type: "quote", content: quoted.join("\n") });
      continue;
    }

    const unordered = line.match(/^\s*[-+*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      const listType = ordered ? "ordered-list" : "list";
      const matcher = ordered ? /^\s*\d+[.)]\s+(.+)$/ : /^\s*[-+*]\s+(.+)$/;
      const items = [];
      while (index < lines.length) {
        const item = lines[index].match(matcher);
        if (!item) break;
        items.push(item[1]);
        index += 1;
      }
      blocks.push({ type: listType, items });
      continue;
    }

    const paragraph = [line.trim()];
    index += 1;
    while (index < lines.length && lines[index].trim() && !startsBlock(lines[index])) {
      paragraph.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ type: "paragraph", content: paragraph.join(" ") });
  }
  return blocks;
}


function startsBlock(line) {
  return /^\s*```/.test(line)
    || /^(#{1,6})\s+/.test(line)
    || /^\s*(?:[-+*]\s+|\d+[.)]\s+|>)/.test(line)
    || /^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line);
}


function renderBlock(block, key) {
  if (block.type === "heading") {
    const Heading = `h${block.level}`;
    return <Heading key={key}>{renderInline(block.content, `${key}-heading`)}</Heading>;
  }
  if (block.type === "rule") return <hr key={key} />;
  if (block.type === "quote") return <blockquote key={key}><MarkdownContent content={block.content} /></blockquote>;
  if (block.type === "list" || block.type === "ordered-list") {
    const List = block.type === "ordered-list" ? "ol" : "ul";
    return <List key={key}>{block.items.map((item, itemIndex) => <li key={itemIndex}>{renderInline(item, `${key}-${itemIndex}`)}</li>)}</List>;
  }
  if (block.type === "code") {
    const language = block.language === "py" ? "python" : block.language;
    return <div className="markdown-code-block" key={key}>
      {language && <span>{language}</span>}
      {language === "python" || language === "json"
        ? <HighlightedCode code={block.content} language={language} ariaLabel={`${language} code block`} />
        : <pre><code>{block.content}</code></pre>}
    </div>;
  }
  return <p key={key}>{renderInline(block.content, `${key}-paragraph`)}</p>;
}


function renderInline(source, keyPrefix) {
  const pattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|~~[^~]+~~|\[[^\]]+\]\([^)]+\)|\*[^*]+\*|_[^_]+_)/g;
  const output = [];
  let cursor = 0;
  let match;
  let part = 0;
  while ((match = pattern.exec(source)) !== null) {
    if (match.index > cursor) output.push(source.slice(cursor, match.index));
    const token = match[0];
    const key = `${keyPrefix}-${part++}`;
    if (token.startsWith("`")) output.push(<code key={key}>{token.slice(1, -1)}</code>);
    else if (token.startsWith("**") || token.startsWith("__")) output.push(<strong key={key}>{renderInline(token.slice(2, -2), key)}</strong>);
    else if (token.startsWith("~~")) output.push(<del key={key}>{renderInline(token.slice(2, -2), key)}</del>);
    else if (token.startsWith("[")) {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      const href = safeLink(link?.[2]);
      output.push(href
        ? <a key={key} href={href} target="_blank" rel="noreferrer">{link[1]}</a>
        : <span key={key}>{link?.[1] || token}</span>);
    } else output.push(<em key={key}>{renderInline(token.slice(1, -1), key)}</em>);
    cursor = match.index + token.length;
  }
  if (cursor < source.length) output.push(source.slice(cursor));
  return output;
}


function safeLink(value = "") {
  const link = String(value).trim();
  return /^(?:https?:\/\/|mailto:)/i.test(link) ? link : "";
}

