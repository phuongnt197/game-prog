import { useEffect, useMemo, useRef, useState } from "react";
import { get, post, streamPost } from "../api/client";
import { HighlightedCode, SyntaxEditor } from "../components/SyntaxCode";
import { MarkdownContent } from "../components/MarkdownContent";
import { ProblemNavigator } from "../components/studio/ProblemNavigator";
import { COPY_PASTE_DISABLED_MESSAGE, scheduleClipboardNoticeDismissal } from "../editor/clipboardGuard";


export function HumanCodePage() {
  const [problems, setProblems] = useState([]);
  const [selectedId, setSelectedId] = useState();
  const [solution, setSolution] = useState("");
  const [tests, setTests] = useState("");
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState("");
  const [streamed, setStreamed] = useState("");
  const [status, setStatus] = useState("");
  const [testResult, setTestResult] = useState();
  const [submission, setSubmission] = useState();
  const [busy, setBusy] = useState(false);
  const [chatting, setChatting] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [testResultsVisible, setTestResultsVisible] = useState(false);
  const [testResultsExpanded, setTestResultsExpanded] = useState(true);
  const [testResultStale, setTestResultStale] = useState(false);
  const [submissionVisible, setSubmissionVisible] = useState(false);
  const [submissionExpanded, setSubmissionExpanded] = useState(true);
  const [submissionStale, setSubmissionStale] = useState(false);
  const [draftMessage, setDraftMessage] = useState("");
  const solutionRef = useRef("");
  const testsRef = useRef("");

  const load = async () => {
    const data = await get("/api/human-code");
    setProblems(data.problems);
    setSelectedId((current) => current || data.problems.find((item) => !item.completed)?.id || data.problems[0]?.id);
  };
  useEffect(() => { load().catch((nextError) => setError(nextError.message)); }, []);
  useEffect(() => error === COPY_PASTE_DISABLED_MESSAGE ? scheduleClipboardNoticeDismissal(setError) : undefined, [error]);
  const problem = useMemo(() => problems.find((item) => item.id === selectedId), [problems, selectedId]);

  useEffect(() => {
    if (!problem) return;
    const nextSolution = problem.solution_code || "";
    const nextTests = problem.test_code || "";
    solutionRef.current = nextSolution;
    testsRef.current = nextTests;
    setSolution(nextSolution);
    setTests(nextTests);
    setMessages([]);
    setPrompt("");
    setTestResult(undefined);
    setTestResultsVisible(false);
    setTestResultsExpanded(true);
    setTestResultStale(false);
    setSubmission(undefined);
    setSubmissionVisible(false);
    setSubmissionExpanded(true);
    setSubmissionStale(false);
    setDraftMessage("");
    setError("");
  }, [selectedId, problem?.id]);

  const updateSolution = (nextSolution) => {
    solutionRef.current = nextSolution;
    setSolution(nextSolution);
    if (testResult) setTestResultStale(true);
    if (submission) setSubmissionStale(true);
    setDraftMessage("");
  };
  const updateTests = (nextTests) => {
    testsRef.current = nextTests;
    setTests(nextTests);
    setDraftMessage("");
  };
  const currentWork = () => ({
    solution_code: solutionRef.current,
    test_code: testsRef.current,
  });
  const save = async () => {
    setBusy(true); setError("");
    try { await post(`/api/human-code/${problem.id}/draft`, currentWork()); setDraftMessage("Draft saved for your next session."); }
    catch (nextError) { setError(nextError.message); }
    finally { setBusy(false); }
  };
  const runTests = async () => {
    setBusy(true); setError("");
    try {
      setTestResult(await post(`/api/human-code/${problem.id}/run-tests`, currentWork()));
      setTestResultsVisible(true);
      setTestResultsExpanded(true);
      setTestResultStale(false);
    }
    catch (nextError) { setError(nextError.message); }
    finally { setBusy(false); }
  };
  const submit = async () => {
    setBusy(true); setError("");
    try {
      const work = currentWork();
      const result = await post(`/api/human-code/${problem.id}/submit`, work);
      setSubmission(result);
      setSubmissionVisible(true);
      setSubmissionExpanded(true);
      setSubmissionStale(false);
      setTestResultsExpanded(false);
      setDraftMessage("");
      if (result.passed) {
        setProblems((current) => current.map((item) => item.id === problem.id ? { ...item, completed: true, ...work } : item));
      }
    } catch (nextError) { setError(nextError.message); }
    finally { setBusy(false); }
  };

  const askCopilot = async (suggestedPrompt) => {
    const question = String(suggestedPrompt || prompt).trim();
    if (!question || !problem || chatting) return;
    const history = messages.map((item) => ({ role: item.role, content: item.content }));
    setMessages((current) => [...current, { role: "user", content: question }]);
    setPrompt(""); setStreamed(""); setStatus("Connecting…"); setError(""); setChatting(true);
    try {
      const finalEvent = await streamPost(`/api/human-code/${problem.id}/chat`, {
        ...currentWork(), message: question, history,
      }, (event) => {
        if (event.type === "status") setStatus(event.message);
        if (event.type === "reset") setStreamed("");
        if (event.type === "delta") {
          setStatus("");
          setStreamed((current) => current + event.content);
        }
      });
      if (!finalEvent?.guidance) throw new Error("The copilot did not return guidance.");
      setMessages((current) => [...current, {
        role: "assistant",
        content: finalEvent.guidance,
        test_code: finalEvent.test_code || "",
      }]);
      if (finalEvent.test_code) {
        updateTests(finalEvent.test_code);
        setTestResult(undefined);
        setTestResultsVisible(false);
        setTestResultStale(false);
      }
      setStreamed(""); setStatus("");
    } catch (nextError) { setError(nextError.message); setStatus(""); }
    finally { setChatting(false); }
  };

  const complete = problems.filter((item) => item.completed).length;
  const preview = copilotPreview(streamed);
  return <div className={`human-code-page ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
    <ProblemNavigator
      open={sidebarOpen}
      onToggle={() => setSidebarOpen((open) => !open)}
      title="My Code"
      subtitle="AI-supported testing"
      completeCount={complete}
      problems={problems}
      selectedId={selectedId}
      onSelect={setSelectedId}
      getStatus={(item) => item.completed
        ? { icon: "✓", label: "Complete", tone: "completed" }
        : { icon: "○", label: "Not completed", tone: "pending" }}
    />

    <section className="surface human-solution-panel">
      <header><div><span className="eyebrow">{problem?.difficulty}</span><h2>{problem?.title || "Select a problem"}</h2></div>{problem && <span className={`status ${problem.completed ? "success" : "warning"}`}>{problem.completed ? "✓ Complete" : "○ Not completed"}</span>}</header>
      <section className="problem-statement"><h3>Problem statement</h3><p>{problem?.description}</p></section>
      <div className="solution-editor"><SyntaxEditor value={solution} onChange={updateSolution} language="python" ariaLabel="Student Python solution" minHeight={0} preventClipboard onBlockedClipboard={() => setError(COPY_PASTE_DISABLED_MESSAGE)} historyKey={selectedId} /></div>
      <div className="workspace-actions"><button disabled={busy || !problem} onClick={save}>Save draft</button><button className="primary" disabled={busy || !problem} onClick={submit}>{busy ? "Checking…" : "Submit solution"}</button></div>
      {draftMessage && <div className="notice success human-notice">{draftMessage}</div>}
      {((testResult && testResultsVisible) || (submission && submissionVisible)) && <div className="solution-feedback-stack">
        {testResult && testResultsVisible && <section className={`solution-test-results ${testResultsExpanded ? "is-expanded" : "is-collapsed"}`}>
          <header>
            <div><strong>AI test results</strong><TestResultStatus result={testResult} stale={testResultStale} /></div>
            <div className="result-panel-actions">
              <button onClick={() => setTestResultsExpanded((expanded) => !expanded)} aria-expanded={testResultsExpanded} aria-label={testResultsExpanded ? "Minimize AI test results" : "Expand AI test results"} title={testResultsExpanded ? "Minimize results" : "Expand results"}>{testResultsExpanded ? "−" : "+"}</button>
              <button onClick={() => setTestResultsVisible(false)} aria-label="Close AI test results" title="Close results">×</button>
            </div>
          </header>
          {testResultsExpanded && <VisibleTestResult result={testResult} />}
        </section>}
        {submission && submissionVisible && <section className={`solution-test-results submission-report ${submissionExpanded ? "is-expanded" : "is-collapsed"}`}>
          <header>
            <div><strong>Submission report</strong><SubmissionResultStatus result={submission} stale={submissionStale} /></div>
            <div className="result-panel-actions">
              <button onClick={() => setSubmissionExpanded((expanded) => !expanded)} aria-expanded={submissionExpanded} aria-label={submissionExpanded ? "Minimize submission report" : "Expand submission report"} title={submissionExpanded ? "Minimize report" : "Expand report"}>{submissionExpanded ? "−" : "+"}</button>
              <button onClick={() => setSubmissionVisible(false)} aria-label="Close submission report" title="Close report">×</button>
            </div>
          </header>
          {submissionExpanded && <SubmissionReport result={submission} />}
        </section>}
      </div>}
    </section>

    <div className="human-copilot-column">
      <section className="surface copilot-panel">
        <header><div><span className="eyebrow">AI learning copilot</span><h2>Review, tests, and next steps</h2></div><span className="status info">Live editor context</span></header>
        <div className="copilot-quick-actions"><button onClick={() => askCopilot("Review my current solution and point out conceptual issues without rewriting it.")} disabled={chatting}>Review solution</button><button onClick={() => askCopilot("Write focused unit tests for my current solution using concrete inputs and assertions.")} disabled={chatting}>Write tests</button><button onClick={() => askCopilot("Suggest one conceptual next step without giving implementation code.")} disabled={chatting}>Suggest next step</button></div>
        <div className="copilot-messages">
          {!messages.length && !streamed && <div className="empty-state">Ask the copilot to review your approach, create visible tests, or suggest a conceptual next step.</div>}
          {messages.map((item, index) => <article className={`chat-message ${item.role}`} key={`${item.role}-${index}`}><strong className="chat-message-author">{item.role === "user" ? "You" : "AI copilot"}</strong><MarkdownContent content={item.content} />{item.test_code && <small>Generated tests were placed in the read-only test panel.</small>}</article>)}
          {(streamed || status) && <article className="chat-message assistant streaming"><strong className="chat-message-author">AI copilot</strong><MarkdownContent content={preview.guidance || status} />{preview.tests && <small>Writing visible tests…</small>}</article>}
        </div>
        <form className="copilot-composer" onSubmit={(event) => { event.preventDefault(); askCopilot(); }}><textarea rows="2" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="Ask for a review, tests, or a conceptual hint…" /><button className="primary" disabled={chatting || !prompt.trim()}>{chatting ? "Thinking…" : "Ask AI"}</button></form>
      </section>

      <section className="surface ai-tests-panel">
        <header><div><span className="eyebrow">Visible tests · Read only</span><h2>AI-written unit tests</h2></div><div className="panel-header-actions"><span className={`status ${tests.trim() ? "success" : "warning"}`}>{tests.trim() ? "✓ Ready" : "○ Missing"}</span><button className="primary" disabled={busy || !tests.trim()} onClick={runTests}>Run tests</button></div></header>
        <div className="ai-tests-view">{tests.trim() ? <HighlightedCode code={tests} language="python" ariaLabel="Read-only AI generated Python unit tests" /> : <div className="empty-state">Ask the AI copilot to write tests for your current solution.</div>}</div>
      </section>
    </div>
    {error && <div className="human-global-error error-banner">{error}</div>}
  </div>;
}


function VisibleTestResult({ result }) {
  if (result.error) return <div className="notice error human-notice">{result.error}</div>;
  const summary = result.summary || {};
  return <div className="visible-test-results"><strong>{summary.passed || 0}/{summary.total || 0} visible tests passed</strong><div className="check-list">{(result.checks || []).map((check) => <div className={`check-item ${check.passed ? "pass" : "fail"}`} key={check.name}><strong>{check.passed ? "✓" : "×"} {check.name}</strong><p>{check.message}</p></div>)}</div></div>;
}


function TestResultStatus({ result, stale }) {
  if (stale) return <span className="status warning">↻ Code changed · run again</span>;
  if (result.error || !result.passed) return <span className="status danger">× Needs attention</span>;
  return <span className="status success">✓ All passed</span>;
}


function SubmissionResultStatus({ result, stale }) {
  if (stale) return <span className="status warning">↻ Code changed since submission</span>;
  if (!result.passed) return <span className="status danger">× Not accepted</span>;
  return <span className="status success">✓ Accepted</span>;
}


function SubmissionReport({ result }) {
  const report = result.report || {};
  return <div className="submission-report-body">
    <div className={`notice human-notice ${result.passed ? "success" : "error"}`}>{result.message}</div>
    {report.not_run ? <p className="submission-report-note">The hidden suite was not run because the solution could not be validated or executed.</p> : <div className="submission-summary-grid">
      <div className="pass"><strong>{report.passed_count || 0}</strong><span>Passed</span></div>
      <div className={report.failed_count ? "fail" : "pass"}><strong>{report.failed_count || 0}</strong><span>Failed</span></div>
      <div><strong>{report.total || 0}</strong><span>Total hidden checks</span></div>
    </div>}
    <p className="submission-report-note">Individual hidden inputs and expected outputs remain private.</p>
  </div>;
}


function copilotPreview(raw) {
  const marker = "===TESTS===";
  const index = raw.indexOf(marker);
  return {
    guidance: (index >= 0 ? raw.slice(0, index) : raw).replace(/^\s*GUIDANCE\s*:\s*/i, "").trim(),
    tests: index >= 0 ? raw.slice(index + marker.length).trim() : "",
  };
}
