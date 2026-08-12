import { useEffect, useRef } from "react";

export function ConsolePanel({ logs, onClear }) {
  const consoleRef = useRef(null);
  useEffect(() => { consoleRef.current.scrollTop = consoleRef.current.scrollHeight; }, [logs]);
  return <section className="panel console-panel">
    <div className="panel-header compact"><div><h2>Console</h2><p>Python errors, print output, and test results.</p></div><button onClick={onClear}>Clear</button></div>
    <pre id="console" ref={consoleRef}>{logs.map((item) => <span className={item.kind} key={item.id}>[{item.time}] {item.message}{"\n"}</span>)}</pre>
  </section>;
}
