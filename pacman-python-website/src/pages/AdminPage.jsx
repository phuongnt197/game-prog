import { useEffect, useState } from "react";
import { get, post } from "../api/client";
import { SyntaxEditor } from "../components/SyntaxCode";

const EMPTY_PROBLEM = { id: "", activity_type: "human", title: "", difficulty: "Easy", position: 1, min_student_tests: 10, function_name: "", description: "", reasoning_trace: "", llm_code: "", ground_truth_code: "", hidden_tests: JSON.stringify([{ input: [], expected: null }], null, 2), active: true };

export function AdminPage() {
  const [overview, setOverview] = useState({ users: [], submissions: [], assignment_count: 0 }); const [assignments, setAssignments] = useState([]); const [problems, setProblems] = useState([]); const [editing, setEditing] = useState(EMPTY_PROBLEM); const [problemActivity, setProblemActivity] = useState("human"); const [message, setMessage] = useState("");
  const load = async () => { try { const [admin, assignmentData, problemData] = await Promise.all([get("/api/admin/overview"), get("/api/assignments"), get("/api/admin/learning-problems")]); setOverview(admin); setAssignments(assignmentData.assignments); setProblems(problemData.problems); } catch (e) { setMessage(e.message); } };
  useEffect(() => { load(); }, []);
  const createUser = async (event) => { event.preventDefault(); try { await post("/api/admin/users", Object.fromEntries(new FormData(event.currentTarget))); event.currentTarget.reset(); setMessage("User created."); load(); } catch (e) { setMessage(e.message); } };
  const editProblem = async (id) => { try { const item = await get(`/api/admin/learning-problems/${id}`); setEditing({ ...item, activity_type: item.activity_type || "bug", hidden_tests: JSON.stringify(item.hidden_tests, null, 2) }); } catch (e) { setMessage(e.message); } };
  const saveProblem = async (event) => { event.preventDefault(); try { await post("/api/admin/learning-problems", { ...editing, hidden_tests: JSON.parse(editing.hidden_tests), position: Number(editing.position), min_student_tests: Number(editing.min_student_tests) }); setMessage("Learning problem saved."); await load(); } catch (e) { setMessage(e.message); } };
  const newProblem = () => setEditing({ ...EMPTY_PROBLEM, activity_type: problemActivity === "all" ? "human" : problemActivity, position: problems.length + 1 });
  const unlock = async (userId, assignmentId) => { await post("/api/admin/unlock", { user_id: userId, assignment_id: assignmentId }); setMessage("Assignment unlocked."); };
  const resetPassword = async (userId) => { const password = prompt("Temporary password (at least 6 characters)"); if (password) { await post("/api/admin/reset-password", { user_id: userId, password }); setMessage("Password reset."); } };
  const visibleProblems = problems.filter((problem) => problemActivity === "all" || problem.activity_type === problemActivity);
  return <div className="page-stack admin-page"><div className="page-title"><div><h2>Administration</h2><p>Manage students, progress, and teacher-authored learning problems.</p></div><button onClick={load}>Refresh</button></div>{message && <div className="notice">{message}</div>}
    <div className="admin-layout"><section className="surface admin-card"><h2>Create user</h2><form className="form-stack" onSubmit={createUser}><label>Name<input name="display_name" required /></label><label>Username<input name="username" required /></label><label>Temporary password<input name="password" type="password" minLength="6" required /></label><label>Role<select name="role"><option>student</option><option>admin</option></select></label><button className="primary">Create</button></form></section>
      <section className="surface admin-card wide"><h2>Students</h2><div className="table-wrap"><table><thead><tr><th>User</th><th>Role</th><th>Done</th><th>Runs</th><th>Risk</th><th>Unlock</th><th>Password</th></tr></thead><tbody>{overview.users.map((user) => <UserRow key={user.id} user={user} assignments={assignments} count={overview.assignment_count} onUnlock={unlock} onReset={resetPassword} />)}</tbody></table></div></section>
      <section className="surface admin-card"><div className="section-heading"><div><h2>Learning problems</h2><p>Each problem belongs to exactly one student activity.</p></div><button onClick={newProblem}>New problem</button></div><div className="tab-row admin-problem-tabs"><button className={problemActivity === "human" ? "active" : ""} onClick={() => setProblemActivity("human")}>AI Copilot</button><button className={problemActivity === "bug" ? "active" : ""} onClick={() => setProblemActivity("bug")}>Test AI Code</button><button className={problemActivity === "all" ? "active" : ""} onClick={() => setProblemActivity("all")}>All</button></div><div className="item-list compact">{visibleProblems.map((problem) => <button key={problem.id} onClick={() => editProblem(problem.id)}><strong>{problem.position}. {problem.title}</strong><span>{problem.difficulty} · {activityLabel(problem.activity_type)} · {problem.active ? "Active" : "Hidden"}</span></button>)}</div></section>
      <section className="surface admin-card wide"><LearningProblemForm value={editing} onChange={setEditing} onSubmit={saveProblem} /></section>
      <section className="surface admin-card wide"><h2>Recent submissions</h2><div className="table-wrap"><table><thead><tr><th>ID</th><th>User</th><th>Assignment</th><th>Passed</th><th>Time</th></tr></thead><tbody>{overview.submissions.map((s) => <tr key={s.id}><td>{s.id}</td><td>{s.username}</td><td>{s.assignment_id}</td><td>{s.passed ? "yes" : "no"}</td><td>{s.created_at}</td></tr>)}</tbody></table></div></section>
    </div></div>;
}

function UserRow({ user, assignments, count, onUnlock, onReset }) {
  const [assignment, setAssignment] = useState(assignments[0]?.id || "");
  return <tr><td>{user.display_name}<small>{user.username}</small></td><td>{user.role}</td><td>{user.completed_count}/{count}</td><td>{user.run_count || 0}</td><td>{user.risk_score || 0}</td><td><select value={assignment} onChange={(e) => setAssignment(e.target.value)}>{assignments.map((a) => <option value={a.id} key={a.id}>{a.order}. {a.title}</option>)}</select><button onClick={() => onUnlock(user.id, assignment)}>Unlock</button></td><td><button onClick={() => onReset(user.id)}>Reset</button></td></tr>;
}

function LearningProblemForm({ value, onChange, onSubmit }) {
  const set = (key, next) => onChange({ ...value, [key]: next });
  const copilotOnly = value.activity_type === "human";
  return <form className="form-stack" onSubmit={onSubmit}>
    <div className="section-heading"><div><h2>Problem setup</h2><p>Reference code and hidden tests are visible only to teachers and the private grader.</p></div><label className="checkbox"><input type="checkbox" checked={value.active} onChange={(e) => set("active", e.target.checked)} /> Active</label></div>
    <div className="admin-secret-note"><strong>Teacher-only grading material</strong><p>{copilotOnly ? "The AI Copilot receives the public statement, function signature, and student's live work—but never the reference solution or hidden tests." : "Test AI Code may use the reference privately to generate a faulty attempt. Students never receive the reference solution or hidden tests."}</p></div>
    <div className="form-grid"><label>Activity<select value={value.activity_type} onChange={(e) => set("activity_type", e.target.value)}><option value="human">AI Copilot</option><option value="bug">Test AI Code</option></select></label><label>Problem ID<input value={value.id} onChange={(e) => set("id", e.target.value)} required /></label><label>Title<input value={value.title} onChange={(e) => set("title", e.target.value)} required /></label><label>Difficulty<select value={value.difficulty} onChange={(e) => set("difficulty", e.target.value)}><option>Easy</option><option>Medium</option><option>Hard</option></select></label><label>Position<input type="number" value={value.position} onChange={(e) => set("position", e.target.value)} /></label><label>Function name<input value={value.function_name} onChange={(e) => set("function_name", e.target.value)} required /></label>{value.activity_type !== "human" && <label>Minimum student test functions<input type="number" min="1" max="50" value={value.min_student_tests} onChange={(e) => set("min_student_tests", e.target.value)} title="Students must define at least this many test_* functions." /></label>}</div>
    <label>Problem statement<textarea rows="4" value={value.description} onChange={(e) => set("description", e.target.value)} required /></label>
    <label>Reference solution<span className="field-help">{copilotOnly ? "Used only by the private grader and to derive the starter function signature. It is never included in an AI Copilot request." : "Used privately to generate and grade the faulty-code exercise. It is never sent to students."}</span><SyntaxEditor value={value.ground_truth_code} onChange={(next) => set("ground_truth_code", next)} language="python" ariaLabel="Teacher reference Python solution" minHeight={360} /></label>
    <label>Full hidden grading suite (JSON)<span className="field-help">Used only when the student submits a solution. Each item requires <code>input</code> and <code>expected</code>; neither value is exposed to the student or AI Copilot.</span><SyntaxEditor value={value.hidden_tests} onChange={(next) => set("hidden_tests", next)} language="json" ariaLabel="Teacher hidden grading tests" minHeight={320} /></label>
    <button className="primary">Save problem</button>
  </form>;
}

function activityLabel(activity) {
  if (activity === "human") return "AI Copilot";
  if (activity === "bug") return "Test AI Code";
  return "Test AI Code";
}
