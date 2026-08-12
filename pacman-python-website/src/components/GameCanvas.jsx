import { useEffect, useRef } from "react";
import { CELL_SIZE } from "../game/constants";
import { positionFromKey } from "../game/engine";

const roundRect = (ctx, x, y, width, height, radius) => {
  const r = Math.min(radius, width / 2, height / 2);
  ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + width, y, x + width, y + height, r);
  ctx.arcTo(x + width, y + height, x, y + height, r); ctx.arcTo(x, y + height, x, y, r);
  ctx.arcTo(x, y, x + width, y, r); ctx.closePath();
};

function draw(ctx, canvas, game, lastAction) {
  ctx.fillStyle = "#050711"; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "rgba(255,255,255,.04)"; ctx.lineWidth = 1;
  for (let x = 0; x <= game.width; x += 1) { ctx.beginPath(); ctx.moveTo(x * CELL_SIZE, 0); ctx.lineTo(x * CELL_SIZE, canvas.height); ctx.stroke(); }
  for (let y = 0; y <= game.height; y += 1) { ctx.beginPath(); ctx.moveTo(0, y * CELL_SIZE); ctx.lineTo(canvas.width, y * CELL_SIZE); ctx.stroke(); }
  ctx.fillStyle = "#fff3bf";
  game.food.forEach((item) => { const { x, y } = positionFromKey(item); ctx.beginPath(); ctx.arc(x * CELL_SIZE + 16, y * CELL_SIZE + 16, 3.5, 0, Math.PI * 2); ctx.fill(); });
  game.walls.forEach((item) => { const { x, y } = positionFromKey(item); ctx.fillStyle = "#1f5eff"; roundRect(ctx, x * 32 + 3, y * 32 + 3, 26, 26, 7); ctx.fill(); ctx.strokeStyle = "rgba(255,255,255,.18)"; ctx.stroke(); });
  const colors = ["#ff6b6b", "#cc5de8", "#4dabf7", "#69db7c"];
  game.ghosts.forEach((ghost) => {
    const cx = ghost.x * 32 + 16; const cy = ghost.y * 32 + 16; ctx.fillStyle = colors[ghost.id % colors.length];
    ctx.beginPath(); ctx.arc(cx, cy - 1, 9.6, Math.PI, 0); ctx.lineTo(cx + 9.6, cy + 9); ctx.lineTo(cx + 5, cy + 6); ctx.lineTo(cx, cy + 9); ctx.lineTo(cx - 5, cy + 6); ctx.lineTo(cx - 9.6, cy + 9); ctx.closePath(); ctx.fill();
    ctx.fillStyle = "white"; ctx.beginPath(); ctx.arc(cx - 5, cy - 3, 4, 0, Math.PI * 2); ctx.arc(cx + 5, cy - 3, 4, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#111827"; ctx.beginPath(); ctx.arc(cx - 4, cy - 3, 1.8, 0, Math.PI * 2); ctx.arc(cx + 6, cy - 3, 1.8, 0, Math.PI * 2); ctx.fill();
  });
  const facing = { RIGHT: 0, DOWN: Math.PI / 2, LEFT: Math.PI, UP: Math.PI * 1.5, STOP: 0 }[lastAction] || 0;
  const cx = game.pacman.x * 32 + 16; const cy = game.pacman.y * 32 + 16;
  ctx.fillStyle = "#ffd43b"; ctx.beginPath(); ctx.moveTo(cx, cy); ctx.arc(cx, cy, 12.2, facing + .27 * Math.PI, facing + 1.73 * Math.PI); ctx.closePath(); ctx.fill();
  if (game.gameOver) {
    ctx.fillStyle = "rgba(0,0,0,.62)"; ctx.fillRect(0, 0, canvas.width, canvas.height); ctx.textAlign = "center";
    ctx.fillStyle = game.win ? "#b7f5ce" : "#ffc9c9"; ctx.font = "bold 42px system-ui"; ctx.fillText(game.win ? "YOU WIN" : "GAME OVER", canvas.width / 2, canvas.height / 2 - 8);
    ctx.fillStyle = "#eef2ff"; ctx.font = "16px system-ui"; ctx.fillText(game.status, canvas.width / 2, canvas.height / 2 + 28);
  }
}

export function GameCanvas({ game, lastAction }) {
  const ref = useRef(null);
  useEffect(() => { const canvas = ref.current; draw(canvas.getContext("2d"), canvas, game, lastAction); }, [game, lastAction]);
  return <canvas ref={ref} width={game.width * CELL_SIZE} height={game.height * CELL_SIZE} aria-label="Pacman simulation" />;
}
