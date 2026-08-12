import { buildStudentInputs } from "../game/engine";
import { HighlightedCode } from "./SyntaxCode";

export function Stats({ game }) {
  const values = [
    ["Score", game.score], ["Target", game.targetScore], ["Lives", game.lives],
    ["Food", `${game.startFood.size - game.food.size}/${game.startFood.size}`],
    ["Steps", `${game.steps}/${game.maxSteps}`], ["Status", game.status],
  ];
  return <>
    <div className="stats">{values.map(([label, value]) => <div className="stat-card" key={label}><span>{label}</span><strong title={String(value)}>{value}</strong></div>)}</div>
    <details className="state-box"><summary>Five values passed to choose_action</summary><HighlightedCode code={JSON.stringify(buildStudentInputs(game), null, 2)} language="json" ariaLabel="Values passed to the Pacman Python function" /></details>
  </>;
}
