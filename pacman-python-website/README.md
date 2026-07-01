# Pacman Logic Lab — Pyodide Browser Demo

This is a minimal prototype for a course website where students write Python logic and immediately see Pacman move in a rendered UI.

## What this demo shows

- The student writes only `choose_action(state)`.
- Pyodide runs the student Python inside a Web Worker.
- JavaScript owns the game engine, rules, collision detection, score, ghosts, and rendering.
- Canvas renders the Pacman UI.
- The game loop repeatedly asks Python for one action, then JavaScript applies it.

## Run locally

Do not open `index.html` directly with `file://`. Use a local web server so the browser can load the worker correctly.

```bash
cd pacman-python-website
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000
```

The first load may take a few seconds because Pyodide is downloaded from the CDN.

## Files

```text
index.html          Page layout
styles.css          Styling
app.js              Pacman engine, renderer, game loop, UI controls
pyodide-worker.js   Python runtime worker that loads and executes student code
README.md           This file
```

## Student API

Students receive a `state` object with:

```python
state.pacman          # (x, y)
state.food            # list[(x, y)]
state.ghosts          # list[(x, y)]
state.walls           # set[(x, y)]
state.legal_actions   # list[str]
state.score           # int
state.lives           # int
state.steps           # int
state.width           # int
state.height          # int
```

Helpers available to students:

```python
manhattan_distance(a, b)
state.next_position(pos, action)
state.is_wall(pos)
state.legal_neighbors(pos)
nearest_food(state)
```

## Important production notes

This demo is intended for local testing and architecture validation. For a real course platform, add:

- user login and saved submissions
- server-side authoritative grading
- hidden maps
- replay storage
- stronger timeout/interrupt handling
- anti-tampering checks
- code version history
- structured rubric results
