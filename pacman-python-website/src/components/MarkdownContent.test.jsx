import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { MarkdownContent } from "./MarkdownContent";


describe("AI chat Markdown", () => {
  it("renders headings, emphasis, inline code, and lists", () => {
    const html = renderToStaticMarkup(<MarkdownContent content={"## Review\n\nUse **clear names** and inspect `value`.\n\n- Check zero\n- Check negatives"} />);
    expect(html).toContain("<h2>Review</h2>");
    expect(html).toContain("<strong>clear names</strong>");
    expect(html).toContain("<code>value</code>");
    expect(html).toContain("<ul>");
    expect(html).toContain("<li>Check zero</li>");
  });

  it("uses syntax highlighting for fenced Python", () => {
    const html = renderToStaticMarkup(<MarkdownContent content={"```python\ndef test_zero():\n    assert 0 == 0\n```"} />);
    expect(html).toContain("shared-code-viewer");
    expect(html).toContain("tok-keyword");
  });

  it("allows safe links and rejects executable link schemes", () => {
    const html = renderToStaticMarkup(<MarkdownContent content={"[Docs](https://example.com) [Unsafe](javascript:alert(1))"} />);
    expect(html).toContain('href="https://example.com"');
    expect(html).not.toContain("javascript:");
  });
});
