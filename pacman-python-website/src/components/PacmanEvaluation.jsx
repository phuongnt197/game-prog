import { CUSTOM_LEVEL_ID, CUSTOM_LEVEL_LABEL, LEVELS, REQUIRED_LEVEL_IDS } from "../game/constants";

export function PacmanEvaluation({ results, progress, customValidation, passed, total }) {
  const resultById = Object.fromEntries(results.map((result) => [result.id, result]));
  const challenges = [
    ...REQUIRED_LEVEL_IDS.map((id) => ({ id, label: LEVELS[id].label, target: LEVELS[id].targetScore })),
    { id: CUSTOM_LEVEL_ID, label: CUSTOM_LEVEL_LABEL },
  ];
  return <section className="panel evaluation-panel">
    <div className="panel-header compact">
      <div><h2>Challenge Report</h2><p>{progress || "Win and meet the target score on every required map."}</p></div>
      <span className={`status-pill ${passed === total ? "status-ready" : ""}`}>{passed}/{total} passed</span>
    </div>
    <div className="evaluation-cards">
      {challenges.map((challenge) => {
        const result = resultById[challenge.id];
        const mapBlocked = challenge.id === CUSTOM_LEVEL_ID && !customValidation.valid;
        const state = result ? (result.passed ? "pass" : "fail") : mapBlocked ? "blocked" : "pending";
        return <article className={`evaluation-card is-${state}`} key={challenge.id}>
          <span className="evaluation-icon" aria-hidden="true">{state === "pass" ? "✓" : state === "fail" ? "×" : state === "blocked" ? "!" : "○"}</span>
          <div>
            <strong>{challenge.label}</strong>
            {result
              ? <><span>Score {result.score} / {result.targetScore}</span><small>{result.status} · {result.steps} steps · {result.deaths} deaths</small></>
              : <><span>{mapBlocked ? "Finish the level design" : `Target ${challenge.target ?? "based on food count"}`}</span><small>{mapBlocked ? customValidation.errors[0] : "Not evaluated yet"}</small></>}
          </div>
        </article>;
      })}
    </div>
  </section>;
}
