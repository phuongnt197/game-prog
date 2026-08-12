export class PythonRuntime {
  constructor({ onStatus, onOutput }) {
    this.onStatus = onStatus;
    this.onOutput = onOutput;
    this.worker = null;
    this.requestId = 0;
    this.pending = new Map();
  }

  start() {
    this.stop("Python worker restarted.");
    this.onStatus({ ready: false, text: "Loading Pyodide…", mode: "loading" });
    this.worker = new Worker(new URL("../../pyodide-worker.js", import.meta.url));
    this.worker.onmessage = ({ data: message = {} }) => {
      if (message.type === "ready") {
        this.onStatus({ ready: true, text: `Pyodide ${message.pyodideVersion} ready`, mode: "ready" });
        return;
      }
      if (message.type === "fatal") {
        this.onStatus({ ready: false, text: "Pyodide failed", mode: "error" });
        this.onOutput(`Fatal worker error: ${message.error}`, "bad");
        return;
      }
      const pending = this.pending.get(message.id);
      if (pending) {
        clearTimeout(pending.timer); this.pending.delete(message.id);
        message.ok === false || message.type === "error"
          ? pending.reject(new Error(message.error || "Python worker error."))
          : pending.resolve(message);
      } else if (message.type === "error") this.onOutput(`Worker error: ${message.error}`, "bad");
    };
    this.worker.onerror = ({ message }) => {
      this.onStatus({ ready: false, text: "Worker crashed", mode: "error" });
      this.onOutput(`Worker crashed: ${message}`, "bad");
    };
  }

  stop(reason = "Python worker stopped.") {
    this.worker?.terminate();
    this.pending.forEach(({ reject, timer }) => { clearTimeout(timer); reject(new Error(reason)); });
    this.pending.clear(); this.worker = null;
  }

  request(payload, timeoutMs = 4000) {
    if (!this.worker) return Promise.reject(new Error("Python worker is not available."));
    const id = ++this.requestId;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        const error = new Error(`Python timed out after ${timeoutMs} ms. Check for an infinite loop or very slow search.`);
        error.isTimeout = true; reject(error);
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer });
      this.worker.postMessage({ ...payload, id });
    });
  }
}
