import { describe, expect, it } from "vitest";
import { CUSTOM_LEVEL_ROWS, REQUIRED_LEVEL_IDS } from "./constants";
import { buildStudentInputs, getLegalActions, gradeGame, nextPosition, parseLevel, positionKey, stepGame } from "./engine";

const shortestFoodAction = (game) => {
  const start = { ...game.pacman };
  const danger = new Set();
  game.ghosts.forEach((ghost) => {
    danger.add(positionKey(ghost));
    getLegalActions(ghost, game, false).forEach((action) => danger.add(positionKey(nextPosition(ghost, action))));
  });
  const search = (blocked) => {
    const queue = [{ position: start, firstAction: undefined }];
    const seen = new Set([positionKey(start)]);
    while (queue.length) {
      const { position, firstAction } = queue.shift();
      if (firstAction && game.food.has(positionKey(position))) return firstAction;
      getLegalActions(position, game, false).forEach((action) => {
        const candidate = nextPosition(position, action);
        const key = positionKey(candidate);
        if (!seen.has(key) && !blocked.has(key)) {
          seen.add(key);
          queue.push({ position: candidate, firstAction: firstAction || action });
        }
      });
    }
    return undefined;
  };
  return search(danger) || search(new Set()) || "STOP";
};

describe("game engine", () => {
  it("parses levels into five simple function inputs", () => {
    const game = parseLevel("classic"); const inputs = buildStudentInputs(game);
    expect(inputs.pacman).toEqual([1, 1]);
    expect(inputs.walls.length).toBeGreaterThan(0);
    expect(Object.keys(inputs)).toEqual(["pacman", "food", "ghosts", "walls", "legal_actions"]);
  });

  it("only exposes legal moves", () => {
    const game = parseLevel("classic");
    expect(getLegalActions(game.pacman, game)).toEqual(["DOWN", "RIGHT", "STOP"]);
  });

  it("applies movement, food, and step scoring", () => {
    const game = parseLevel("classic"); const action = stepGame(game, "RIGHT");
    expect(action).toBe("RIGHT"); expect(game.pacman).toEqual({ x: 2, y: 1 });
    expect(game.food.has("2,1")).toBe(false); expect(game.score).toBe(14); expect(game.steps).toBe(1);
  });

  it("penalizes illegal moves and stops Pacman", () => {
    const game = parseLevel("classic"); stepGame(game, "UP");
    expect(game.pacman).toEqual({ x: 1, y: 1 }); expect(game.illegalMoves).toBe(1); expect(game.score).toBe(-6);
  });

  it("loads a custom map and grades both win and target score", () => {
    const game = parseLevel("custom", CUSTOM_LEVEL_ROWS);
    expect(game.label).toBe("My Level");
    expect(game.targetScore).toBeGreaterThan(200);
    game.win = true; game.score = game.targetScore;
    expect(gradeGame(game).passed).toBe(true);
    game.score -= 1;
    expect(gradeGame(game).passed).toBe(false);
  });

  it("keeps the required starter maps achievable by a function-only path strategy", () => {
    REQUIRED_LEVEL_IDS.forEach((id) => {
      const game = parseLevel(id);
      while (!game.gameOver) stepGame(game, shortestFoodAction(game));
      const result = gradeGame(game);
      expect(result.passed, `${id} should be winnable above its visible target: ${JSON.stringify(result)}`).toBe(true);
    });
  });
});
