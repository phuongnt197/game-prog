import { useEffect, useState } from "react";
import { get } from "../api/client";

export function ShowcasePage() {
  const [projects, setProjects] = useState([]); const [error, setError] = useState("");
  const load = () => get("/api/projects").then((d) => setProjects(d.projects)).catch((e) => setError(e.message));
  useEffect(load, []);
  return <div className="page-stack showcase-page"><div className="page-title"><div><h2>AIP1 Showcase</h2><p>Previously published student projects</p></div><button onClick={load}>Refresh</button></div>{error && <p className="error-banner">{error}</p>}<div className="card-grid">{projects.map((project) => <article className="surface project-card" key={project.slug}><span className="eyebrow">{project.template_id}</span><h3>{project.title}</h3><p>{project.description}</p><small>Created by {project.creator}</small></article>)}{!projects.length && <div className="empty-state">No published projects yet.</div>}</div></div>;
}
