export function ProblemNavigator({
  open,
  onToggle,
  title,
  subtitle,
  completeCount,
  problems,
  selectedId,
  onSelect,
  getStatus,
}) {
  const allComplete = problems.length > 0 && completeCount === problems.length;
  return <aside className={`surface sidebar bug-sidebar ${open ? "is-open" : "is-collapsed"}`}>
    <button className="bug-sidebar-toggle" onClick={onToggle} aria-expanded={open} aria-label={open ? "Collapse problem navigator" : "Expand problem navigator"} title={open ? "Collapse problems" : "Show problems"}>{open ? "←" : "☰"}</button>
    {open && <div className="bug-sidebar-content">
      <div className="section-heading">
        <div><h2>{title}</h2><p>{subtitle}</p></div>
        <span className={`pill ${allComplete ? "is-complete" : "is-incomplete"}`}>{completeCount}/{problems.length}</span>
      </div>
      <div className="item-list problem-nav-list">{problems.map((item) => {
        const itemStatus = getStatus(item);
        return <button
          key={item.id}
          className={`problem-nav-item ${item.id === selectedId ? "selected" : ""} ${itemStatus.tone}`}
          onClick={() => onSelect(item.id)}
          aria-current={item.id === selectedId ? "page" : undefined}
        >
          <strong>{item.position}. {item.title}</strong>
          <span className="problem-nav-status"><b aria-hidden="true">{itemStatus.icon}</b>{item.difficulty} · {itemStatus.label}</span>
        </button>;
      })}</div>
    </div>}
  </aside>;
}
