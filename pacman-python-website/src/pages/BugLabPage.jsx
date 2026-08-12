import { useEffect, useMemo, useState } from "react";
import { get, post, streamPost } from "../api/client";
import { HighlightedCode, SyntaxEditor } from "../components/SyntaxCode";
import { ProblemNavigator } from "../components/studio/ProblemNavigator";
import { COPY_PASTE_DISABLED_MESSAGE, scheduleClipboardNoticeDismissal } from "../editor/clipboardGuard";

const GENERATION_MARKER = "===PYTHON===";

const testTemplate = (problem) => `# Write at least ${problem?.min_student_tests || 10} independent test functions.
# Every test must call ${problem?.function_name || "the_function"}(...) with concrete inputs
# and use at least one assert statement.

def test_example_case():
    result = ${problem?.function_name || "the_function"}(...)
    assert result == ...
`;

export function BugLabPage() {
  const [problems, setProblems] = useState([]);
  const [selectedId, setSelectedId] = useState();
  const [tests, setTests] = useState("");
  const [fixed, setFixed] = useState("");
  const [validation, setValidation] = useState();
  const [fixResult, setFixResult] = useState();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [generationRaw, setGenerationRaw] = useState("");
  const [generationStatus, setGenerationStatus] = useState("");
  const [workStage, setWorkStage] = useState("tests");

  const load = async () => {
    const data = await get("/api/bug-problems");
    setProblems(data.problems);
    setSelectedId((id) => id || data.problems.find((item) => !item.progress.completed)?.id || data.problems[0]?.id);
  };

  useEffect(() => { load().catch((nextError) => setError(nextError.message)); }, []);
  useEffect(() => error === COPY_PASTE_DISABLED_MESSAGE ? scheduleClipboardNoticeDismissal(setError) : undefined, [error]);
  const problem = useMemo(() => problems.find((item) => item.id === selectedId), [problems, selectedId]);

  useEffect(() => {
    if (!problem) return;
    setTests(problem.progress?.student_test_code || testTemplate(problem));
    setFixed(problem.llm_code);
    setValidation(problem.progress?.tests_passed && problem.progress?.student_test_code
      ? { gate_passed: true, restored: true }
      : undefined);
    setFixResult(undefined);
    setError("");
    setGenerationRaw("");
    setGenerationStatus("");
    setWorkStage(problem.progress?.tests_passed ? "fix" : "tests");
  }, [selectedId, problem]);

  const generate = async () => {
    if (!problem) return;
    setGenerating(true);
    setGenerationRaw("");
    setGenerationStatus("Connecting to the LLM…");
    setError("");
    try {
      const finalEvent = await streamPost(`/api/bug-problems/${problem.id}/generate`, {}, (event) => {
        if (event.type === "status") setGenerationStatus(event.message);
        if (event.type === "delta") setGenerationRaw((current) => current + event.content);
      });
      if (!finalEvent?.generated) throw new Error("The LLM did not produce a solution.");
      setProblems((current) => current.map((item) => item.id === problem.id ? {
        ...item,
        generated: true,
        reasoning_trace: finalEvent.reasoning_trace,
        llm_code: finalEvent.llm_code,
      } : item));
      setGenerationStatus("LLM solution ready.");
    } catch (nextError) {
      setError(nextError.message);
      setGenerationStatus("");
    } finally {
      setGenerating(false);
    }
  };

  const validate = async () => {
    const wasAlreadyUnlocked = Boolean(problem?.progress.tests_passed);
    setBusy(true);
    setError("");
    try {
      const data = await post(`/api/bug-problems/${problem.id}/validate-tests`, { test_code: tests });
      setValidation(data);
      if (data.gate_passed) {
        problem.progress.tests_passed = true;
        problem.progress.student_test_code = tests;
        setProblems([...problems]);
        if (!wasAlreadyUnlocked) setWorkStage("fix");
      }
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setBusy(false);
    }
  };

  const submit = async () => {
    setBusy(true);
    setError("");
    try {
      const data = await post(`/api/bug-problems/${problem.id}/submit-fix`, { corrected_code: fixed });
      setFixResult(data);
      if (data.passed) {
        problem.progress.completed = true;
        setProblems([...problems]);
      }
    } catch (nextError) {
      setError(nextError.message);
    } finally {
      setBusy(false);
    }
  };

  const complete = problems.filter((item) => item.progress.completed).length;
  const unlocked = Boolean(problem?.progress.tests_passed || validation?.gate_passed);
  const activeStage = unlocked ? workStage : "tests";
  const generationPreview = useMemo(() => parseGenerationPreview(generationRaw), [generationRaw]);

  return <div className={`bug-page ${sidebarOpen ? "" : "sidebar-collapsed"}`}>
    <ProblemNavigator
      open={sidebarOpen}
      onToggle={() => setSidebarOpen((open) => !open)}
      title="Detecting AI Bugs"
      subtitle="Test first, then repair"
      completeCount={complete}
      problems={problems}
      selectedId={selectedId}
      onSelect={setSelectedId}
      getStatus={(item) => item.progress.completed
        ? { icon: "✓", label: "Complete", tone: "completed" }
        : item.progress.tests_passed
          ? { icon: "◐", label: "Fix unlocked", tone: "in-progress" }
          : item.generated
            ? { icon: "◐", label: "Write tests", tone: "in-progress" }
            : { icon: "○", label: "Generate solution", tone: "pending" }}
    />

    <section className="surface brief-panel bug-problem-panel">
        <header><span className="eyebrow">{problem?.difficulty}</span><h2>{problem?.title || "Select a problem"}</h2></header>
        <section className="problem-statement" aria-labelledby="problem-statement-heading"><h3 id="problem-statement-heading">Problem statement</h3><p>{problem?.description}</p></section>
        {problem?.generated ? <div className="bug-reference-grid">
          <div><h3>LLM solution rationale</h3><pre className="reasoning">{problem.reasoning_trace}</pre></div>
          <div><h3>LLM final program</h3><HighlightedCode code={problem.llm_code} language="python" ariaLabel="LLM final Python program" /></div>
        </div> : <div className="generation-card">
          <span className="eyebrow">On-demand LLM attempt</span>
          <h3>Generate the solution to review</h3>
          <p>The LLM will produce a concise rationale and a Python program. Your task will be to test that generated program.</p>
          <button className="primary" disabled={generating || !problem} onClick={generate}>{generating ? "Generating…" : "Generate LLM solution"}</button>
          {generationStatus && <div className="generation-status">{generationStatus}</div>}
          {generationRaw && <div className="generation-preview">
            <h3>LLM solution rationale</h3><pre className="reasoning">{generationPreview.reasoning || "Generating rationale…"}</pre>
            {generationPreview.code && <><h3>LLM final program</h3><HighlightedCode code={generationPreview.code} language="python" ariaLabel="Streaming LLM Python program" /></>}
          </div>}
        </div>}
    </section>

    <div className="bug-work-column">
      {problem?.generated ? <section className={`surface test-workspace ${unlocked ? "has-stage-tabs" : ""}`}>
        {unlocked && <div className="tab-row bug-stage-tabs" role="tablist" aria-label="Test AI Code stages">
          <button role="tab" aria-selected={activeStage === "tests"} className={activeStage === "tests" ? "active" : ""} onClick={() => setWorkStage("tests")}>✓ Unit tests</button>
          <button role="tab" aria-selected={activeStage === "fix"} className={activeStage === "fix" ? "active" : ""} onClick={() => setWorkStage("fix")}>{problem.progress.completed ? "✓" : "2."} Correction</button>
        </div>}

        {activeStage === "tests" && <div className="test-stage">
          <div className="step-heading"><span>1</span><div><h2>{unlocked ? "Practice unit tests" : "Write unit tests"}</h2><p>{unlocked ? "Correction stays unlocked. Add more independent tests and validate them whenever you want more practice." : <>Define at least {problem?.min_student_tests || 10} zero-parameter <code>test_*</code> functions. Each must call <code>{problem?.function_name}(...)</code> with concrete inputs and assert the expected behavior.</>}</p></div></div>
          <div className="stage-editor"><SyntaxEditor value={tests} onChange={setTests} language="python" ariaLabel="Student Python unit tests" minHeight={0} preventClipboard onBlockedClipboard={() => setError(COPY_PASTE_DISABLED_MESSAGE)} historyKey={`${selectedId}:tests`} /></div>
          <div className="workspace-actions"><button className="primary" disabled={busy || !problem} onClick={validate}>{busy ? "Checking…" : "Validate tests"}</button></div>
        </div>}

        {activeStage === "fix" && <div className="fix-stage">
          <div className="step-heading"><span>2</span><div><h2>Correct the solution</h2><p>Your unit tests passed. Repair the implementation; the complete admin suite remains hidden.</p></div></div>
          <div className="stage-editor"><SyntaxEditor value={fixed} onChange={setFixed} language="python" ariaLabel="Corrected Python solution" minHeight={0} preventClipboard onBlockedClipboard={() => setError(COPY_PASTE_DISABLED_MESSAGE)} historyKey={`${selectedId}:fix`} /></div>
          <div className="workspace-actions"><button className="primary" disabled={busy} onClick={submit}>{busy ? "Checking…" : "Submit correction"}</button></div>
        </div>}
      </section> : <section className="surface generation-placeholder"><h2>Unit-test workspace</h2><p>Generate the LLM solution before writing tests.</p></section>}
      <BugResultsPanel validation={validation} fixResult={fixResult} error={error} unlocked={unlocked} activeStage={activeStage} generated={Boolean(problem?.generated)} generating={generating} />
    </div>
  </div>;
}

function BugResultsPanel({ validation, fixResult, error, unlocked, activeStage, generated, generating }) {
  const showValidation = activeStage === "tests" && validation;
  const showFixResult = activeStage === "fix" && fixResult;
  const showEmpty = !showValidation && !showFixResult && !error;
  const statusLabel = !generated
    ? (generating ? "Generating" : "Awaiting LLM")
    : !unlocked
      ? "Stage 1"
      : activeStage === "tests" ? "Test practice" : "Fix unlocked";
  return <aside className="surface bug-results-panel">
    <div className="section-heading"><div><h2>Results</h2><p>Validation and grading feedback</p></div><span className={`status ${unlocked ? "" : "info"}`}>{statusLabel}</span></div>
    {error && <p className="error-banner">{error}</p>}
    {showEmpty && <div className="empty-state">{!generated ? "Generate the LLM solution to begin." : activeStage === "fix" ? "Submit your corrected solution to see hidden-suite grading results." : "Run your unit tests to see structural checks, captured inputs, and bug-detection results."}</div>}
    {showValidation && <section className="result-section"><h3>Unit-test validation</h3><ValidationResult result={validation} /></section>}
    {showFixResult && <section className="result-section"><h3>Correction grading</h3><div className={`notice result-notice ${fixResult.passed ? "success" : "error"}`}>{fixResult.passed ? "Correction accepted. Problem complete." : "The correction does not pass the full hidden suite yet."}</div><CorrectionResult result={fixResult} /></section>}
  </aside>;
}

function parseGenerationPreview(raw) {
  const markerIndex = raw.indexOf(GENERATION_MARKER);
  const rationalePart = markerIndex >= 0 ? raw.slice(0, markerIndex) : raw;
  const codePart = markerIndex >= 0 ? raw.slice(markerIndex + GENERATION_MARKER.length) : "";
  return {
    reasoning: rationalePart.replace(/^\s*(?:RATIONALE|REASONING)\s*:\s*/i, "").trim(),
    code: codePart.replace(/^\s*```(?:python)?\s*/i, "").replace(/\s*```\s*$/i, "").trim(),
  };
}

function ValidationResult({ result }) {
  if (result.restored) return <div className="notice success result-notice">This Python test suite was previously validated.</div>;
  const summary = result.summary || {};
  const req = result.requirements || {};
  const rows = [
    ["Minimum functions", req.count, `${summary.test_count || 0}/${summary.minimum || 0}`],
    ["Calls assigned function", req.calls_function, "Every test_* function"],
    ["Contains assertions", req.has_assertions, "Every test_* function"],
    ["Zero parameters", req.zero_parameters, "Directly runnable tests"],
    ["Keeps assigned binding", req.safe_binding, "Function is not redefined"],
    ["Unique test names", req.unique_names, "No overwritten tests"],
    ["Unique inputs", req.unique_inputs, `${summary.unique_count || 0} captured`],
    ["Ground-truth valid", req.valid, `${summary.valid_count || 0}/${summary.test_count || 0}`],
    ["Detects bug", req.detects_bug, `${summary.detected_count || 0} detecting`],
  ];
  return <>
    <div className="validation-grid">{rows.map(([label, pass, value]) => <div className={pass ? "pass" : "fail"} key={label}><strong>{pass ? "✓" : "×"} {label}</strong><span>{value}</span></div>)}</div>
    <div className="check-list">{(result.checks || []).map((check) => <div className={`check-item ${check.valid ? "pass" : "fail"}`} key={check.name}><strong>{check.valid ? "✓" : "×"} {check.name}</strong><p>{check.message}</p>{check.inputs?.length > 0 && <code>Inputs: {JSON.stringify(check.inputs)}</code>}</div>)}</div>
  </>;
}

function CorrectionResult({ result }) {
  const checks = result.correction_checks || [];
  const passed = checks.filter((check) => check.passed).length;
  return <>
    <p className="result-summary">{passed}/{checks.length} hidden tests passed</p>
    <div className="check-list">{checks.map((check) => <div className={`check-item ${check.passed ? "pass" : "fail"}`} key={check.name}><strong>{check.passed ? "✓" : "×"} {check.name}</strong><p>{check.passed ? "Passed" : "Failed"}</p></div>)}</div>
  </>;
}
