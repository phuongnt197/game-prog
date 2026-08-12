# AIP1 Studio React Frontend

This is the single frontend for AIP1 Studio. It contains Learning Fundamentals, Test AI Code, AI Copilot, AI Education, Pacman Agent, Showcase, Admin, and Account pages.

## Development

Start FastAPI from the repository root:

```bash
source .venv/bin/activate
python app.py
```

Then start Vite in another terminal:

```bash
cd pacman-python-website
npm install
npm run dev
```

Vite serves the frontend on `http://localhost:5173` and proxies `/api` to FastAPI on port `8002`.

## Production

```bash
cd pacman-python-website
npm run build
cd ..
source .venv/bin/activate
python app.py
```

FastAPI serves the compiled React application and API together on `http://localhost:8002`.

## Verification

```bash
cd pacman-python-website && npm test && npm run build
cd .. && .venv/bin/python -m unittest discover -s tests -v
```

Pyodide runs the function-based Pacman bot in a browser Web Worker. Judge0 remains responsible for server-side assignment and bug-lab execution.
