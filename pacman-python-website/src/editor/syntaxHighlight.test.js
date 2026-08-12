import { describe, expect, it } from "vitest";
import { highlightCode, highlightJson } from "./syntaxHighlight";

describe("shared syntax highlighting", () => {
  it("highlights JSON keys, strings, values, and punctuation", () => {
    const result = highlightJson('{"active": true, "count": 12, "value": null}');
    expect(result).toContain('class="tok-json-key"');
    expect(result).toContain('class="tok-bool"');
    expect(result).toContain('class="tok-number"');
    expect(result).toContain('class="tok-null"');
  });

  it("uses the existing Python tokenizer", () => {
    const result = highlightCode("def answer():\n    return 42", "python");
    expect(result).toContain('<span class="tok-keyword">def</span>');
    expect(result).toContain('<span class="tok-number">42</span>');
  });

  it("escapes markup before displaying source", () => {
    expect(highlightJson('{"value": "<script>"}')).toContain("&lt;script&gt;");
  });
});
