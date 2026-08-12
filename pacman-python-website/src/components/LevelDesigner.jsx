import { useState } from "react";
import { CUSTOM_LEVEL_ROWS } from "../game/constants";
import { LEVEL_TOOLS, cloneRows, fillEmptyWithFood, paintLevel } from "../game/levelDesigner";

const TILE_NAMES = { "#": "wall", ".": "food", P: "Pacman", G: "ghost", " ": "empty" };
const TILE_GLYPHS = { "#": "", ".": "•", P: "P", G: "G", " ": "" };

export function LevelDesigner({ rows, validation, onChange, onUse }) {
  const [tool, setTool] = useState("#");
  return <div className="level-designer">
    <div className="level-designer-heading">
      <div><h2>Design My Level</h2><p>Choose a tile, then click inside the map. Your map saves automatically.</p></div>
      <span className={`status ${validation.valid ? "success" : "danger"}`}>{validation.valid ? "✓ Ready" : "! Incomplete"}</span>
    </div>
    <div className="level-toolbox" aria-label="Level drawing tools">
      {LEVEL_TOOLS.map(({ tile, label }) => <button key={label} className={tool === tile ? "selected" : ""} onClick={() => setTool(tile)} aria-pressed={tool === tile}><span className={`level-tool-icon tile-${TILE_NAMES[tile]}`}>{TILE_GLYPHS[tile]}</span>{label}</button>)}
    </div>
    <div className="level-grid-wrap">
      <div className="level-grid" style={{ gridTemplateColumns: `repeat(${rows[0].length}, 1fr)` }} aria-label="Custom Pacman level editor">
        {rows.flatMap((row, y) => [...row].map((tile, x) => {
          const border = y === 0 || y === rows.length - 1 || x === 0 || x === row.length - 1;
          return <button
            type="button"
            key={`${x}-${y}`}
            className={`level-cell tile-${TILE_NAMES[tile]} ${border ? "is-border" : ""}`}
            onClick={() => onChange(paintLevel(rows, x, y, tool))}
            disabled={border}
            aria-label={`Row ${y + 1}, column ${x + 1}: ${TILE_NAMES[tile]}`}
            title={`${TILE_NAMES[tile]} (${x}, ${y})`}
          >{TILE_GLYPHS[tile]}</button>;
        }))}
      </div>
    </div>
    <div className="level-designer-summary">
      <span><strong>{validation.counts.food || 0}</strong> food</span>
      <span><strong>{validation.counts.ghosts || 0}</strong> ghosts</span>
      <span><strong>{validation.counts.pacman || 0}</strong> Pacman</span>
    </div>
    {!validation.valid && <ul className="level-errors">{validation.errors.map((error) => <li key={error}>{error}</li>)}</ul>}
    <div className="level-designer-actions">
      <button onClick={() => onChange(fillEmptyWithFood(rows))}>Fill empty with food</button>
      <button onClick={() => onChange(cloneRows(CUSTOM_LEVEL_ROWS))}>Reset example</button>
      <button className="primary" disabled={!validation.valid} onClick={onUse}>Play this level</button>
    </div>
  </div>;
}
