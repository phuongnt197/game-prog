export function WorldGrid({ world, trace = [] }) {
  if (!world) return <div className="empty-state">Select an open assignment.</div>;
  const last = trace.at(-1) || { x: world.start?.[0], y: world.start?.[1], gems: world.gems || [] };
  const walls = new Set((world.walls || []).map((p) => p.join(","))); const gems = new Set((last.gems || world.gems || []).map((p) => p.join(",")));
  return <div className="world-grid" style={{ gridTemplateColumns: `repeat(${world.width},1fr)` }}>
    {Array.from({ length: world.width * world.height }, (_, index) => { const x = index % world.width; const y = Math.floor(index / world.width); const key = `${x},${y}`; const classes = ["world-cell"];
      if (walls.has(key)) classes.push("wall"); if (world.goal?.[0] === x && world.goal?.[1] === y) classes.push("goal"); if (gems.has(key)) classes.push("gem"); if (last.x === x && last.y === y) classes.push("agent");
      return <span className={classes.join(" ")} key={key} />; })}
  </div>;
}

export function CheckList({ checks = [] }) {
  return <div className="check-list">{checks.map((check, index) => <div className={`check-item ${check.passed ? "pass" : "fail"}`} key={`${check.name}-${index}`}><strong>{check.passed ? "✓" : "×"} {check.name}</strong><p>{check.details || check.message || ""}</p></div>)}</div>;
}
