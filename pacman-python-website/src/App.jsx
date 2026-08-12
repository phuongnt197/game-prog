import { useEffect, useState } from "react";
import { get } from "./api/client";
import { AuthScreen } from "./components/studio/AuthScreen";
import { AppShell } from "./components/studio/AppShell";
import { AccountPage } from "./pages/AccountPage";
import { AdminPage } from "./pages/AdminPage";
import { AiEducationPage } from "./pages/AiEducationPage";
import { BugLabPage } from "./pages/BugLabPage";
import { FundamentalsPage } from "./pages/FundamentalsPage";
import { HumanCodePage } from "./pages/HumanCodePage";
import { PacmanPage } from "./pages/PacmanPage";

const PAGES = { fundamentals: FundamentalsPage, bugs: BugLabPage, humanCode: HumanCodePage, aiEducation: AiEducationPage, pacman: PacmanPage, admin: AdminPage, account: AccountPage };

export default function App() {
  const [user, setUser] = useState(undefined); const [view, setView] = useState("fundamentals");
  useEffect(() => { get("/api/me").then(({ user: current }) => { setUser(current); if (current?.must_change_password) setView("account"); }).catch(() => setUser(null)); }, []);
  if (user === undefined) return <div className="loading-screen">Loading AIP1 Studio…</div>;
  if (!user) return <AuthScreen onAuthenticated={(current) => { setUser(current); setView(current.must_change_password ? "account" : "fundamentals"); }} />;
  const Page = PAGES[view] || FundamentalsPage;
  const navigate = async (next) => { try { const data = await get("/api/me"); if (data.user) setUser(data.user); } finally { setView(next); } };
  return <AppShell user={user} view={view} onView={navigate}><Page user={user} onUser={setUser} onNavigate={navigate} /></AppShell>;
}
