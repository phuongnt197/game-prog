# Game-based Programming Environment

## Current Status

The repository now contains a working local web app for an introductory Python learning environment:

- A beginner programming roadmap with locked/unlocked assignments, starter code, visual grid missions, run/submit checks, autosaved drafts, and progress tracking.
- A SQLite-backed user system with student registration, admin-created users, sessions, password changes, and role-based access.
- An admin view for checking student progress, recent submissions, behavior indicators, manual unlocks, and password resets.
- A Pacman agent prototype embedded into the main app and also available as a standalone browser demo.

## How to Run

From the repository root:

```bash
python app.py
```

Then open:

```text
http://localhost:8001
```

The server listens on `0.0.0.0:8001` by default. Runtime data is created under `data/`, including the SQLite database.

## Default Login

On the first run, the app creates one admin account:

```text
username: admin
password: admin123
```

The default admin password should be changed after login. Students can also self-register from the login screen.

## Main User Flows

1. Log in or create a student account.
2. Use the **Roadmap** tab to complete assignments in order.
3. Run code on a visible debug map, then submit to run all assignment checks.
4. Use the **Admin** tab, when logged in as an admin, to monitor progress and unlock assignments manually.
5. Use **Pacman Agent** to open the separate Pacman logic prototype.

## Important Files

```text
app.py                         Main entry point; starts server_v2
studio/server_v2.py       Current HTTP server, routes, auth, assignments, admin, studio, Pacman mount
studio/db.py              SQLite schema, users, sessions, progress, submissions, behavior logs, projects
studio/assignments.py     Roadmap assignment definitions and grid-agent grading harness
studio/harness.py         Project Studio run/test harness for Judge0
studio/judge0.py          Judge0 client
studio/llm.py             OpenAI-compatible AI helper client
studio/templates.py       Project Studio starter templates
studio/config.py          Environment variables and default service settings
static/                        Main AIP1 Studio frontend
pacman-python-website/         Standalone Pacman/Pyodide prototype
```

## Configuration

The app uses these environment variables when needed:

```text
AIP1_HOST              default: 0.0.0.0
AIP1_PORT              default: 8001
AIP1_DB_PATH           default: data/studio.sqlite3
AIP1_ADMIN_USERNAME    default: admin
AIP1_ADMIN_PASSWORD    default: admin123
JUDGE0_HOST            default: http://<URL>
JUDGE0_PORT            default: 2358 
JUDGE0_LANGUAGE_ID     default: 33
OPENAI_BASE_URL        default: http://<URL>
OPENAI_MODEL           default: Qwen/Qwen3.6-35B-A3B
OPENAI_API_KEY         default: EMPTY
```

JUDGE0 and OPENAI currently are not being used.
