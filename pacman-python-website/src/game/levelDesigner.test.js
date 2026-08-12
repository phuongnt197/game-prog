import { describe, expect, it } from "vitest";
import { CUSTOM_LEVEL_ROWS, LEVELS } from "./constants";
import { fillEmptyWithFood, paintLevel, validateCustomLevel } from "./levelDesigner";

describe("custom Pacman level designer", () => {
  it("accepts the supplied editable level", () => {
    const result = validateCustomLevel(CUSTOM_LEVEL_ROWS);
    expect(result.valid).toBe(true);
    expect(result.counts.pacman).toBe(1);
    expect(result.counts.ghosts).toBeGreaterThan(0);
    expect(result.counts.food).toBeGreaterThanOrEqual(10);
  });

  it("keeps every built-in map connected and playable", () => {
    Object.entries(LEVELS).forEach(([id, level]) => {
      expect(validateCustomLevel(level.rows), `${id} should be a valid connected maze`).toMatchObject({ valid: true });
    });
  });

  it("moves the unique Pacman start when painting", () => {
    const changed = paintLevel(CUSTOM_LEVEL_ROWS, 2, 1, "P");
    expect(changed.join("").match(/P/g)).toHaveLength(1);
    expect(changed[1][2]).toBe("P");
  });

  it("protects the outer wall and detects unreachable food", () => {
    expect(paintLevel(CUSTOM_LEVEL_ROWS, 0, 0, " ")).toEqual(CUSTOM_LEVEL_ROWS);
    const rows = fillEmptyWithFood([
      "########",
      "#P..#G.#",
      "#...#..#",
      "#...#..#",
      "#...#..#",
      "########",
    ]);
    expect(validateCustomLevel(rows).errors).toContain("Every food pellet and ghost must be reachable from Pacman.");
  });
});
