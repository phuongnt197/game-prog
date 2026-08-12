import { ACTIONS, CUSTOM_LEVEL_ID, CUSTOM_LEVEL_LABEL, DIRECTIONS, LEVELS } from "./constants";

export const positionKey = ({ x, y }) => `${x},${y}`;
export const positionFromKey = (value) => {
  const [x, y] = value.split(",").map(Number);
  return { x, y };
};

export function scoreTargetForRows(rows) {
  const foodCount = rows.reduce((total, row) => total + [...row].filter((cell) => cell === ".").length, 0);
  return 200 + foodCount * 10;
}

export function parseLevel(name, customRows) {
  const definition = name === CUSTOM_LEVEL_ID
    ? { label: CUSTOM_LEVEL_LABEL, rows: customRows, targetScore: scoreTargetForRows(customRows || []) }
    : LEVELS[name];
  if (!definition?.rows?.length) throw new Error(`Unknown level: ${name}`);
  return parseLevelRows(name, definition.rows, definition);
}

export function parseLevelRows(name, rows, options = {}) {
  const [width, height] = [rows[0]?.length || 0, rows.length];
  const walls = new Set();
  const food = new Set();
  const ghosts = [];
  let pacman;

  rows.forEach((row, y) => {
    if (row.length !== width) throw new Error(`Level ${name} row ${y + 1} has inconsistent width.`);
    [...row].forEach((cell, x) => {
      if (cell === "#") walls.add(positionKey({ x, y }));
      if (cell === ".") food.add(positionKey({ x, y }));
      if (cell === "P") pacman = { x, y };
      if (cell === "G") ghosts.push({ x, y, startX: x, startY: y });
    });
  });
  if (!pacman) throw new Error(`Level ${name} has no Pacman start position.`);

  const identifiedGhosts = ghosts.map((ghost, id) => ({ ...ghost, id }));
  return {
    name,
    label: options.label || name,
    width,
    height,
    walls,
    food,
    startFood: new Set(food),
    pacman: { ...pacman },
    startPacman: { ...pacman },
    ghosts: identifiedGhosts.map((ghost) => ({ ...ghost })),
    startGhosts: identifiedGhosts.map((ghost) => ({ ...ghost })),
    score: 0,
    targetScore: Number(options.targetScore ?? scoreTargetForRows(rows)),
    lives: 4,
    steps: 0,
    maxSteps: Math.max(180, Math.min(360, food.size * 5)),
    illegalMoves: 0,
    collisions: 0,
    gameOver: false,
    win: false,
    status: "Ready",
  };
}

export function nextPosition(pos, action) {
  const direction = DIRECTIONS[action] || DIRECTIONS.STOP;
  return { x: pos.x + direction.x, y: pos.y + direction.y };
}

export function isWall(pos, game) {
  return pos.x < 0 || pos.y < 0 || pos.x >= game.width || pos.y >= game.height || game.walls.has(positionKey(pos));
}

export function getLegalActions(pos, game, includeStop = true) {
  const actions = ACTIONS.slice(0, 4).filter((action) => !isWall(nextPosition(pos, action), game));
  return includeStop ? [...actions, "STOP"] : actions;
}

export function normalizeAction(action) {
  const normalized = String(action || "STOP").trim().toUpperCase();
  return ACTIONS.includes(normalized) ? normalized : "STOP";
}

export function buildStudentInputs(game) {
  const toTuple = (item) => {
    const { x, y } = positionFromKey(item);
    return [x, y];
  };
  return {
    pacman: [game.pacman.x, game.pacman.y],
    food: [...game.food].map(toTuple),
    ghosts: game.ghosts.map(({ x, y }) => [x, y]),
    walls: [...game.walls].map(toTuple),
    legal_actions: getLegalActions(game.pacman, game),
  };
}

export function gradeGame(game) {
  const passed = Boolean(game.win && game.score >= game.targetScore);
  return {
    id: game.name,
    label: game.label,
    passed,
    win: Boolean(game.win),
    score: game.score,
    targetScore: game.targetScore,
    steps: game.steps,
    deaths: game.collisions,
    illegalMoves: game.illegalMoves,
    foodLeft: game.food.size,
    status: passed ? "Target achieved" : !game.win ? game.status : "Won, but score is below target",
  };
}

const distance = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);

function handleCollision(game) {
  game.collisions += 1;
  game.lives -= 1;
  game.score -= 75;
  if (game.lives <= 0) {
    Object.assign(game, { gameOver: true, win: false, status: "Game over: caught by a ghost" });
  } else {
    game.status = "Caught! Positions reset.";
    game.pacman = { ...game.startPacman };
    game.ghosts = game.startGhosts.map((ghost) => ({ ...ghost }));
  }
}

const hasCollision = (game) => game.ghosts.some(({ x, y }) => x === game.pacman.x && y === game.pacman.y);

function moveGhosts(game) {
  if (game.steps % 2 !== 0) return;
  game.ghosts.forEach((ghost) => {
    const scored = getLegalActions(ghost, game, false).map((action) => {
      const candidate = nextPosition(ghost, action);
      return { candidate, distance: distance(candidate, game.pacman), tie: (ACTIONS.indexOf(action) + game.steps + ghost.id) % 4 };
    }).sort((a, b) => a.distance - b.distance || a.tie - b.tie);
    if (scored[0]) Object.assign(ghost, scored[0].candidate);
  });
}

export function stepGame(game, requestedAction) {
  if (game.gameOver) return "STOP";
  let action = normalizeAction(requestedAction);
  if (!getLegalActions(game.pacman, game).includes(action)) {
    game.illegalMoves += 1;
    game.score -= 5;
    action = "STOP";
  }
  game.steps += 1;
  game.score -= 1;
  const candidate = nextPosition(game.pacman, action);
  if (!isWall(candidate, game)) game.pacman = candidate;
  if (game.food.delete(positionKey(game.pacman))) game.score += 15;
  if (hasCollision(game)) {
    handleCollision(game);
    return action;
  }
  moveGhosts(game);
  if (hasCollision(game)) {
    handleCollision(game);
    return action;
  }
  if (game.food.size === 0) Object.assign(game, { gameOver: true, win: true, score: game.score + 250, status: "Win: all food collected" });
  else if (game.steps >= game.maxSteps) Object.assign(game, { gameOver: true, win: false, status: "Stopped: max steps reached" });
  else game.status = `Last action: ${action}`;
  return action;
}
