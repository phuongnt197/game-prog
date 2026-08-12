import { useEffect, useMemo, useState } from "react";
import { get, post } from "../api/client";
import { CheckList, WorldGrid } from "../components/studio/WorldGrid";
import { SyntaxEditor } from "../components/SyntaxCode";
import { COPY_PASTE_DISABLED_MESSAGE, scheduleClipboardNoticeDismissal } from "../editor/clipboardGuard";

export function FundamentalsPage() {
  const [assignments, setAssignments] = useState([]); const [selectedId, setSelectedId] = useState(); const [code, setCode] = useState("");
  const [caseIndex, setCaseIndex] = useState(0); const [result, setResult] = useState({}); const [busy, setBusy] = useState(false); const [message, setMessage] = useState("");
  const load = async () => { const data = await get("/api/assignments"); setAssignments(data.assignments); setSelectedId((current) => current || data.assignments.find((x) => x.unlocked && !x.completed)?.id || data.assignments.find((x) => x.unlocked)?.id); };
  useEffect(() => { load().catch((e) => setMessage(e.message)); }, []);
  useEffect(() => message === COPY_PASTE_DISABLED_MESSAGE ? scheduleClipboardNoticeDismissal(setMessage) : undefined, [message]);
  const selected = useMemo(() => assignments.find((x) => x.id === selectedId), [assignments, selectedId]);
  useEffect(() => { if (selected) { setCode(selected.draft_code ?? selected.starter_code ?? ""); setCaseIndex(selected.cases?.[0]?.index || 0); setResult({}); } }, [selectedId, selected]);
  const execute = async (submit) => { if (!selected) return; setBusy(true); setMessage(""); try { const data = await post(`/api/assignments/${selected.id}/${submit ? "submit" : "run"}`, submit ? { code } : { code, case_index: caseIndex }); setResult(data); if (data.completed) { setMessage("Assignment complete. The next mission is unlocked."); await load(); } } catch (e) { setMessage(e.message); } finally { setBusy(false); } };
  const save = async () => { if (!selected) return; await post(`/api/assignments/${selected.id}/draft`, { code }); setMessage("Draft saved."); };
  const completed = assignments.filter((item) => item.completed).length;
  return <div className="three-column-page fundamentals-page">
    <aside className="surface sidebar"><div className="section-heading"><div><h2>Assignments</h2><p>Python foundations</p></div><span className="pill">{completed}/{assignments.length}</span></div><div className="item-list">{assignments.map((item) => <button key={item.id} disabled={!item.unlocked} className={item.id === selectedId ? "selected" : ""} onClick={() => setSelectedId(item.id)}><strong>{item.order}. {item.title}</strong><span>{item.completed ? "Complete" : item.unlocked ? "Open" : "Locked"} · {item.concept}</span></button>)}</div></aside>
    <section className="surface code-workspace tab-code-workspace"><header><div><span className="eyebrow">{selected?.stage || "Learning Fundamentals"}</span><h2>{selected?.title || "Select an assignment"}</h2><p>{selected?.summary}</p></div>{selected && <span className={`status ${selected.completed ? "success" : "info"}`}>{selected.completed ? "Complete" : "Open"}</span>}</header><div className="instructions">{selected?.instructions}</div><div className="toolbar"><div><button className="primary" disabled={busy || !selected} onClick={() => execute(false)}>Run</button><button disabled={busy || !selected} onClick={() => execute(true)}>Submit</button><button onClick={save} disabled={!selected}>Save</button><button onClick={() => setCode(selected?.starter_code || "")}>Reset</button></div>{selected?.cases?.length > 1 && <select value={caseIndex} onChange={(e) => setCaseIndex(Number(e.target.value))}>{selected.cases.map((c) => <option value={c.index} key={c.index}>{c.name}</option>)}</select>}</div><div className="tab-editor-scroll"><SyntaxEditor value={code} onChange={setCode} language="python" ariaLabel="Learning Fundamentals Python editor" minHeight={0} preventClipboard onBlockedClipboard={() => setMessage(COPY_PASTE_DISABLED_MESSAGE)} historyKey={selectedId} /></div>{message && <div className="notice workspace-notice">{message}</div>}</section>
    <aside className="surface results-panel"><h2>Agent</h2><WorldGrid world={result.world || selected?.cases?.find((c) => c.index === caseIndex)?.world || selected?.world} trace={result.trace} /><h2>Checks</h2><CheckList checks={result.checks} /><h2>Console</h2><pre className="output">{result.stdout || result.error || "Run code to see results."}</pre></aside>
  </div>;
}
