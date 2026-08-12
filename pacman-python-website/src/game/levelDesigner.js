import { CUSTOM_LEVEL_MIN_FOOD, CUSTOM_LEVEL_ROWS, DIRECTIONS } from "./constants";

export const LEVEL_TOOLS = [
  { tile: "#", label: "Wall" },
  { tile: ".", label: "Food" },
  { tile: "P", label: "Pacman" },
  { tile: "G", label: "Ghost" },
  { tile: " ", label: "Empty" },
];

export const cloneRows = (rows = CUSTOM_LEVEL_ROWS) => rows.map((row) => String(row));

export function validateCustomLevel(rows) {
  const errors = [];
  if (!Array.isArray(rows) || rows.length < 6) return { valid: false, errors: ["The level needs at least 6 rows."], counts: {} };
  const width = rows[0]?.length || 0;
  if (width < 8) errors.push("The level needs at least 8 columns.");
  if (rows.some((row) => typeof row !== "string" || row.length !== width)) errors.push("Every map row must have the same width.");
  if (rows.some((row) => [...row].some((tile) => !"#.PG ".includes(tile)))) errors.push("The map contains an unsupported tile.");

  const cells = rows.join("");
  const counts = {
    pacman: [...cells].filter((tile) => tile === "P").length,
    ghosts: [...cells].filter((tile) => tile === "G").length,
    food: [...cells].filter((tile) => tile === ".").length,
  };
  if (counts.pacman !== 1) errors.push("Place exactly one Pacman start tile.");
  if (counts.ghosts < 1 || counts.ghosts > 4) errors.push("Place between 1 and 4 ghosts.");
  if (counts.food < CUSTOM_LEVEL_MIN_FOOD) errors.push(`Place at least ${CUSTOM_LEVEL_MIN_FOOD} food pellets.`);

  if (width && rows.every((row) => row.length === width)) {
    const borderIsClosed = [...rows[0], ...rows[rows.length - 1]].every((tile) => tile === "#")
      && rows.every((row) => row[0] === "#" && row[width - 1] === "#");
    if (!borderIsClosed) errors.push("Keep a complete wall border around the map.");
  }

  if (!errors.length) {
    const start = findTile(rows, "P");
    const reachable = reachableTiles(rows, start);
    const unreachableTargets = [];
    rows.forEach((row, y) => [...row].forEach((tile, x) => {
      if ((tile === "." || tile === "G") && !reachable.has(`${x},${y}`)) unreachableTargets.push([x, y]);
    }));
    if (unreachableTargets.length) errors.push("Every food pellet and ghost must be reachable from Pacman.");
  }

  return { valid: errors.length === 0, errors, counts, width, height: rows.length };
}

export function paintLevel(rows, x, y, tile) {
  if (!LEVEL_TOOLS.some((tool) => tool.tile === tile)) return cloneRows(rows);
  const next = rows.map((row) => [...row]);
  if (!next[y]?.[x] || y === 0 || y === next.length - 1 || x === 0 || x === next[y].length - 1) return cloneRows(rows);
  if (tile === "P") {
    next.forEach((row) => row.forEach((value, column) => {
      if (value === "P") row[column] = " ";
    }));
  }
  next[y][x] = tile;
  return next.map((row) => row.join(""));
}

export function fillEmptyWithFood(rows) {
  return rows.map((row, y) => [...row].map((tile, x) => {
    const border = y === 0 || y === rows.length - 1 || x === 0 || x === row.length - 1;
    return !border && tile === " " ? "." : tile;
  }).join(""));
}

function findTile(rows, target) {
  for (let y = 0; y < rows.length; y += 1) {
    const x = rows[y].indexOf(target);
    if (x >= 0) return { x, y };
  }
  return undefined;
}

function reachableTiles(rows, start) {
  if (!start) return new Set();
  const seen = new Set([`${start.x},${start.y}`]);
  const queue = [start];
  while (queue.length) {
    const current = queue.shift();
    ["UP", "DOWN", "LEFT", "RIGHT"].forEach((action) => {
      const { x: dx, y: dy } = DIRECTIONS[action];
      const x = current.x + dx;
      const y = current.y + dy;
      const key = `${x},${y}`;
      if (rows[y]?.[x] && rows[y][x] !== "#" && !seen.has(key)) {
        seen.add(key);
        queue.push({ x, y });
      }
    });
  }
  return seen;
}
