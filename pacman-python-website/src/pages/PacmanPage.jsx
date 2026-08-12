import { useState } from "react";
import { CodeEditor } from "../components/CodeEditor";
import { ConsolePanel } from "../components/ConsolePanel";
import { GameCanvas } from "../components/GameCanvas";
import { LevelDesigner } from "../components/LevelDesigner";
import { PacmanEvaluation } from "../components/PacmanEvaluation";
import { Stats } from "../components/Stats";
import { CUSTOM_LEVEL_ID, CUSTOM_LEVEL_LABEL, LEVELS } from "../game/constants";
import { usePacmanGame } from "../hooks/usePacmanGame";

export function PacmanPage({ user }) {
  const app = usePacmanGame(user?.id || "local");
  const [buildTab, setBuildTab] = useState("code");
  const disabled = !app.runtimeStatus.ready || app.evaluating;
  const blockClipboard = (event) => {
    event.preventDefault();
    app.log("Copy and paste are disabled in the Pacman editor.", "warn");
  };
  return <div className="pacman-workspace">
    <header className="workspace-header">
      <div><p className="workspace-kicker">Bot &amp; level project</p><h1>Pacman Agent</h1><p className="workspace-subtitle">Write one Python function, design a maze, and reach the target score on the starter maps and your own level.</p></div>
      <div className="pacman-header-status"><span className={`status-pill ${app.passedChallengeCount === app.requiredChallengeCount ? "status-ready" : ""}`}>{app.passedChallengeCount}/{app.requiredChallengeCount} challenges</span><span className={`status-pill status-${app.runtimeStatus.mode}`}>{app.runtimeStatus.text}</span></div>
    </header>
    <div className="layout pacman-layout">
      <section className="panel pacman-build-panel">
        <div className="pacman-build-tabs" role="tablist" aria-label="Pacman project editors">
          <button role="tab" aria-selected={buildTab === "code"} className={buildTab === "code" ? "active" : ""} onClick={() => setBuildTab("code")}>1. Bot function</button>
          <button role="tab" aria-selected={buildTab === "level"} className={buildTab === "level" ? "active" : ""} onClick={() => setBuildTab("level")}>2. My level <span className={`tab-state ${app.customValidation.valid ? "complete" : "missing"}`}>{app.customValidation.valid ? "✓" : "!"}</span></button>
        </div>
        {buildTab === "code" ? <>
          <div className="panel-header"><div><h2>Strategy Function</h2><p>No classes or objects are required—work with tuples and lists.</p></div><button className="primary" disabled={disabled} onClick={app.loadCode}>Load function</button></div>
          <CodeEditor code={app.code} onChange={app.updateCode} onBlockedClipboard={blockClipboard} />
          <div className="hint-grid"><div><strong>Define</strong><span>choose_action(pacman, food, ghosts, walls, legal_actions)</span></div><div><strong>Helpers provided</strong><span>move(...) · manhattan_distance(...) · nearest_food(...) · legal_neighbors(...)</span></div></div>
        </> : <LevelDesigner rows={app.customRows} validation={app.customValidation} onChange={app.updateCustomRows} onUse={() => app.setLevel(CUSTOM_LEVEL_ID)} />}
      </section>
      <section className="panel game-panel">
        <div className="panel-header compact"><div><h2>Simulation</h2><p>Debug one map, then evaluate every required challenge.</p></div><label className="map-picker"><span>Map</span><select value={app.level} disabled={app.running || app.evaluating} onChange={(event) => app.setLevel(event.target.value)}>{Object.entries(LEVELS).map(([id, definition]) => <option value={id} key={id}>{definition.label}{definition.required ? " · required" : " · practice"}</option>)}<option value={CUSTOM_LEVEL_ID} disabled={!app.customValidation.valid}>{CUSTOM_LEVEL_LABEL} · required</option></select></label></div>
        <div className="simulation-controls" aria-label="Pacman simulation controls">
          <button disabled={disabled || app.running} onClick={app.step} title="Advance the selected level by one bot decision">Step</button>
          <button className="primary" disabled={disabled} onClick={app.toggleRun} title="Play or pause the selected level">{app.running ? "Pause" : "Play"}</button>
          <button disabled={app.evaluating} onClick={() => app.reset()} title="Reset the selected level to its starting state">Reset</button>
          <button disabled={disabled || app.running || !app.customValidation.valid} onClick={app.evaluateBot} title="Run the bot against every required starter level and your custom level">{app.evaluating ? "Testing…" : "Run tests"}</button>
        </div>
        <div className="canvas-wrap"><GameCanvas game={app.game} lastAction={app.lastAction} /></div>
        <div className="game-simulation-footer">
          <Stats game={app.game} />
        </div>
      </section>
    </div>
    <div className="pacman-bottom-panels">
      <PacmanEvaluation results={app.evaluation} progress={app.evaluationProgress} customValidation={app.customValidation} passed={app.passedChallengeCount} total={app.requiredChallengeCount} />
      <ConsolePanel logs={app.logs} onClear={app.clearLogs} />
    </div>
  </div>;
}
