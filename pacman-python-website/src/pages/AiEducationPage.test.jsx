import { describe, expect, it } from "vitest";
import { parseEducationPreview } from "./AiEducationPage";


describe("AI education stream preview", () => {
  it("separates streamed Markdown from the animation plan", () => {
    const preview = parseEducationPreview("EXPLANATION:\n## Recursion\nWatch the stack.\n===ANIMATION_PLAN===\n```json\n{\"title\": \"Call stack\"}\n");
    expect(preview.explanation).toContain("## Recursion");
    expect(preview.explanation).not.toContain("===ANIMATION_PLAN===");
    expect(preview.animationPlan).toContain("Call stack");
    expect(preview.animationPlan).not.toContain("```json");
  });

  it("shows explanation tokens before the marker arrives", () => {
    expect(parseEducationPreview("EXPLANATION:\nBinary search removes").explanation).toBe("Binary search removes");
    expect(parseEducationPreview("EXPLANATION:\nBinary search removes").animationPlan).toBe("");
  });
});
