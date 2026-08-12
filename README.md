# Game-based Programming Environment

AIP1 Studio uses a React/Vite frontend and a modular FastAPI backend. SQLite stores users, progress, and AI learning problems. Judge0 executes server-validated Python, the Pacman page uses Pyodide in a browser worker, and the AI Education page uses Manim Community to render generated concept videos.

## First-time setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cd pacman-python-website
npm install
npm run build
cd ..
```

Manim on Linux also requires Cairo and Pango development libraries. On Debian/Ubuntu, install them before the Python requirements:

```bash
sudo apt install build-essential python3-dev libcairo2-dev libpango1.0-dev
```

Generated lesson videos are stored under `data/ai_education/`. Each user keeps their five most recent renders. The renderer timeout can be configured with `MANIM_RENDER_TIMEOUT` (120 seconds by default).

## Run production locally

```bash
python app.py
```

Open `http://localhost:8002`. FastAPI documentation is available at `http://localhost:8002/docs`.

Configuration:

```bash
AIP1_HOST=127.0.0.1 AIP1_PORT=8002 python app.py
```

## Frontend development

If you wish to develop the frontend, first, run FastAPI, then in a second terminal:

```bash
cd pacman-python-website
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://127.0.0.1:8002`.

## Main User Flows

1. Log in or create a student account.
2. Use the **Roadmap** tab to complete assignments in order.
3. Run code on a visible debug map, then submit to run all assignment checks.
4. Use the **Admin** tab, when logged in as an admin, to monitor progress and unlock assignments manually.
5. Use **Pacman Agent** to open the separate Pacman logic prototype.

## Structure

```text
aip1_studio/api/          FastAPI app, dependencies, schemas, routers
aip1_studio/services/     Judge0 and evaluation orchestration
aip1_studio/db.py         SQLite persistence
pacman-python-website/    Unified React/Vite frontend
tests/                    Backend and evaluation tests
```

## Pacman student API

Pacman is the course project. Students design a validated custom maze and implement one plain Python function—no classes are required:

```python
def choose_action(pacman, food, ghosts, walls, legal_actions):
    return "STOP"
```

Positions are `(x, y)` tuples, and collections are lists of tuples. The browser provides `move`, `manhattan_distance`, `nearest_food`, and `legal_neighbors` helper functions. Evaluation requires a win and target score on two starter maps and the student's custom map.

## Configuration

The app uses these environment variables when needed:

```text
AIP1_HOST              default: localhost
AIP1_PORT              default: 8002
AIP1_DB_PATH           default: data/studio.sqlite3
AIP1_ADMIN_USERNAME    default: admin
AIP1_ADMIN_PASSWORD    default: admin123
JUDGE0_HOST            default: http://<URL>
JUDGE0_PORT            default: 2358 
JUDGE0_LANGUAGE_ID     default: 33
OPENAI_BASE_URL        default: http://<URL>
OPENAI_MODEL           default: Qwen/Qwen3.6-35B-A3B
OPENAI_API_KEY         default: EMPTY
MANIM_RENDER_TIMEOUT   default: 120
```