const NAV = [
  ["fundamentals", "Learning Fundamentals"], ["bugs", "Test AI Code"], ["humanCode", "AI Copilot"], ["aiEducation", "AI Education"],
  ["pacman", "Pacman Agent"], ["admin", "Admin"], ["account", "Account"],
];

export function AppShell({ user, view, onView, children }) {
  return <div className="studio-app"><header className="topbar">
    <div className="brand"><span className="brand-mark">A1</span><div><h1>AIP1 Studio</h1><p>{user.display_name} · {user.role}</p></div></div>
    <nav>{NAV.filter(([id]) => id !== "admin" || user.role === "admin").map(([id, label]) => <button key={id} className={view === id ? "active" : ""} onClick={() => onView(id)}>{label}</button>)}</nav>
  </header><main className="app-content">{children}</main></div>;
}
