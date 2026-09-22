import { copy as uiCopy } from "@/i18n/th";
import { useEffect, useState, type FormEvent } from "react";
import {
  Link,
  Navigate,
  NavLink,
  Outlet,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpen,
  CalendarDays,
  Check,
  ChevronRight,
  FlaskConical,
  FolderHeart,
  GraduationCap,
  Info,
  LoaderCircle,
  LogOut,
  Menu,
  MessageSquare,
  Plus,
  Settings2,
  ShieldCheck,
  Sparkles,
  X,
} from "lucide-react";
import { api, ApiError, errorText, isMock } from "@/api/client";
import { useApiPage } from "@/api/queries";
import type { ChatSessionSummary, CurrentUser, LoginResponse, MeResponse, StudentProfile } from "@/api/types";

/** 02 ไม่มี field ชื่อคนใน /auth/login หรือ /auth/me เลย (มีแค่ username/student_id/role) — ต้อง
 * รวมกับ /students/me/profile เอง (ดู COMPAT_FIX_REPORT.md P1-G) ชื่อที่ใช้แสดงจริงจึงยืมมาจาก username แทน */
async function hydrateUser(base: LoginResponse | MeResponse): Promise<CurrentUser> {
  const profile = await api
    .get<StudentProfile>("/students/me/profile")
    .catch(() => null);
  return { ...base, ...(profile ?? {}) };
}
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Mascot } from "@/components/Mascot";
import { ErrorBox, Loading } from "@/components/Common";
import { useApp } from "@/state";
import { th } from "@/i18n/th";
import Chat from "@/features/Chat";
import Courses from "@/features/Courses";
import { Planner, Plans, PlanDetail, AutoPlans } from "@/features/Plans";
import Profile from "@/features/Profile";

function Login() {
  const { setUser, notify } = useApp(),
    navigate = useNavigate(),
    cache = useQueryClient();
  const [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState<unknown>(null),
    [pending, setPending] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const login = await api.post<LoginResponse>("/auth/login", {
        username,
        password,
      });
      cache.clear();
      setUser(await hydrateUser(login));
      navigate(isMock ? "/chat/1" : "/chat", { replace: true });
      notify(uiCopy.app001);
    } catch (e) {
      setError(e);
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="login-page">
      <div className="login-art">
        <Link className="login-brand" to="/login">
          <Mascot avatar />
          CampusMate<span>.</span>
        </Link>
        <div className="login-story">
          <span className="eyebrow">{uiCopy.app002}</span>
          <h1>
            {uiCopy.app003}
            <br />
            {uiCopy.app004}
          </h1>
          <p>
            {uiCopy.app005}
            <br />
            {uiCopy.app006}
          </p>
          <div className="login-owl">
            <Mascot />
            <span className="floating-note">
              <Check size={16} />
              {uiCopy.app007}
            </span>
          </div>
        </div>
        <small>{uiCopy.app008}</small>
      </div>
      <div className="login-panel">
        <div className="login-form-wrap">
          <span className="login-symbol">
            <GraduationCap size={28} />
          </span>
          <h2>{uiCopy.app009}</h2>
          <p>{uiCopy.app010}</p>
          {isMock && (
            <div className="demo-login">
              <FlaskConical size={18} />
              <span>
                {uiCopy.app011}
                <br />
                <strong>admin</strong> / <strong>admin1234</strong>
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setUsername("admin");
                  setPassword("admin1234");
                }}
              >
                {uiCopy.app012}
              </Button>
            </div>
          )}
          <form onSubmit={submit}>
            <label htmlFor="username">{uiCopy.app013}</label>
            <input
              id="username"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder={uiCopy.app014}
              required
            />
            <label htmlFor="password">{uiCopy.app015}</label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={uiCopy.app016}
              required
            />
            <ErrorBox error={error} />
            <Button className="login-submit" disabled={pending}>
              {pending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <>
                  {uiCopy.app017}
                  <ArrowRight />
                </>
              )}
            </Button>
          </form>
          <div className="login-fine">
            <ShieldCheck size={16} />
            {isMock ? uiCopy.app018 : uiCopy.app019}
          </div>
        </div>
      </div>
    </div>
  );
}
function Shell() {
  const { user, setUser, draft, setDraft, toast, notify } = useApp(),
    navigate = useNavigate(),
    location = useLocation(),
    cache = useQueryClient();
  const [mobile, setMobile] = useState(false),
    [settings, setSettings] = useState(false);
  const sessions = useApiPage<ChatSessionSummary>(
    ["chat-sessions"],
    "/chat/sessions",
  );
  const nav = [
    { path: "/chat", label: th.nav.chat, icon: MessageSquare },
    { path: "/courses", label: th.nav.courses, icon: BookOpen },
    { path: "/planner", label: th.nav.planner, icon: CalendarDays },
    { path: "/plans", label: th.nav.plans, icon: FolderHeart },
    { path: "/profile", label: th.nav.profile, icon: GraduationCap },
  ];
  const title = location.pathname.startsWith("/chat/")
    ? sessions.data?.items.find(
        (s) => String(s.id) === location.pathname.split("/")[2],
      )?.title || uiCopy.app020
    : location.pathname === "/plans/auto"
      ? uiCopy.app021
      : nav.find((n) => location.pathname.startsWith(n.path))?.label ||
        "CampusMate";
  async function logout() {
    try {
      await api.post("/auth/logout", {});
      cache.clear();
      setDraft([]);
      setUser(null);
      navigate("/login", { replace: true });
    } catch (e) {
      notify(errorText(e));
    }
  }
  function open(path: string) {
    navigate(path);
    setMobile(false);
  }
  const sidebar = (
    <>
      <Link to="/chat" className="brand" onClick={() => setMobile(false)}>
        <Mascot avatar className="brand-owl" />
        <span>
          <strong>
            CampusMate<span className="brand-dot">.</span>
          </strong>
          <small>{th.subtitle}</small>
        </span>
      </Link>
      <Button className="new-chat" onClick={() => open("/chat")}>
        <Plus size={20} />
        {th.newChat}
      </Button>
      <nav className="main-nav" aria-label={uiCopy.app022}>
        {nav.map((n) => (
          <NavLink
            to={n.path}
            key={n.path}
            onClick={() => setMobile(false)}
            className={({ isActive }) =>
              `nav-item ${isActive ? "selected" : ""}`
            }
          >
            <n.icon size={20} />
            <span>{n.label}</span>
            {n.path === "/planner" && draft.length > 0 ? (
              <span className="count-pill">{draft.length}</span>
            ) : null}
          </NavLink>
        ))}
      </nav>
      <div className="recent-section">
        <div className="section-label">
          {th.recent}
          <span>{sessions.data?.items.length || 0}</span>
        </div>
        <div className="recent-list">
          {sessions.data?.items.slice(0, 4).map((s) => (
            <NavLink
              key={s.id}
              to={`/chat/${s.id}`}
              className={({ isActive }) =>
                `recent-item ${isActive ? "active" : ""}`
              }
              onClick={() => setMobile(false)}
            >
              <MessageSquare size={14} />
              <span>{s.title}</span>
            </NavLink>
          ))}
        </div>
      </div>
      <div className="sidebar-bottom">
        <div className="mascot-card">
          <span className="tiny-spark spark-one">✦</span>
          <span className="tiny-spark spark-two">✧</span>
          <Mascot />
          <strong>{th.mascot}</strong>
          <p>{th.mascotHint}</p>
        </div>
        <div className="profile">
          <span className="profile-avatar">{uiCopy.app023}</span>
          <span>
            <strong>{user?.username}</strong>
            <small>
              {uiCopy.app024}
              {user?.year_level ?? "-"}
            </small>
          </span>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSettings(true)}
            aria-label={uiCopy.app025}
          >
            <Settings2 size={18} />
          </Button>
        </div>
      </div>
    </>
  );
  return (
    <div className="app-shell">
      <aside className="sidebar">{sidebar}</aside>
      <Dialog open={mobile} onOpenChange={setMobile}>
        <DialogContent className="mobile-sidebar">
          <DialogHeader className="sr-only">
            <DialogTitle>{uiCopy.app026}</DialogTitle>
            <DialogDescription>{uiCopy.app027}</DialogDescription>
          </DialogHeader>
          {sidebar}
        </DialogContent>
      </Dialog>
      <main className="workspace">
        <header className="workspace-header">
          <Button
            variant="ghost"
            size="icon"
            className="mobile-menu"
            onClick={() => setMobile(true)}
            aria-label={uiCopy.app028}
          >
            <Menu />
          </Button>
          <div className="header-title">
            <div className="breadcrumb">
              {uiCopy.app029}
              <ChevronRight size={12} /> {th.term}
            </div>
            <h1>{title}</h1>
            <p>
              {location.pathname.startsWith("/chat")
                ? uiCopy.app030
                : uiCopy.app031}
            </p>
          </div>
          {isMock && (
            <span className="mode-status">
              <FlaskConical size={14} />
              {th.mock}
            </span>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="header-info"
            onClick={() => setSettings(true)}
            aria-label={uiCopy.app032}
          >
            <Info size={19} />
          </Button>
        </header>
        <Outlet />
      </main>
      <Dialog open={settings} onOpenChange={setSettings}>
        <DialogContent>
          <DialogHeader>
            <span className="dialog-symbol">
              <Settings2 />
            </span>
            <DialogTitle>{uiCopy.app033}</DialogTitle>
            <DialogDescription>
              {isMock ? uiCopy.app034 : uiCopy.app035}
            </DialogDescription>
          </DialogHeader>
          <div className="settings-copy">
            <p>
              {uiCopy.app036}
              {user?.username}
            </p>
            <p>{isMock ? uiCopy.app037 : uiCopy.app038}</p>
            {isMock && (
              <Button
                variant="outline"
                onClick={() => {
                  setSettings(false);
                  void api.post("/demo/expire", {}).catch(() => {});
                }}
              >
                {uiCopy.app039}
              </Button>
            )}
            <Button variant="outline" onClick={logout}>
              <LogOut />
              {uiCopy.app040}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      {toast && (
        <div role="status" className="toast">
          <Check size={18} />
          {toast}
        </div>
      )}
    </div>
  );
}
export default function App() {
  const { user, setUser, setDraft } = useApp(),
    [loading, setLoading] = useState(true),
    [error, setError] = useState<unknown>(null),
    navigate = useNavigate(),
    cache = useQueryClient();
  useEffect(() => {
    let active = true;
    api
      .get<MeResponse>("/auth/me")
      .then((u) => hydrateUser(u))
      .then((u) => {
        if (active) setUser(u);
      })
      .catch((e) => {
        if (active && !(e instanceof ApiError && e.code === "AUTH_401"))
          setError(e);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [setUser]);
  useEffect(() => {
    const expire = () => {
      cache.clear();
      setUser(null);
      setDraft([]);
      navigate("/login", { replace: true });
    };
    window.addEventListener("campusmate:unauthorized", expire);
    return () => window.removeEventListener("campusmate:unauthorized", expire);
  }, [cache, navigate, setUser, setDraft]);
  if (loading) return <Loading />;
  if (error)
    return (
      <div className="startup-error">
        <ErrorBox error={error} />
        <Button onClick={() => window.location.reload()}>
          {uiCopy.app041}
        </Button>
      </div>
    );
  return (
    <Routes>
      <Route
        path="/login"
        element={
          user ? (
            <Navigate to={isMock ? "/chat/1" : "/chat"} replace />
          ) : (
            <Login />
          )
        }
      />
      <Route element={user ? <Shell /> : <Navigate to="/login" replace />}>
        <Route
          index
          element={<Navigate to={isMock ? "/chat/1" : "/chat"} replace />}
        />
        <Route path="chat/:sessionId?" element={<Chat />} />
        <Route path="courses" element={<Courses />} />
        <Route path="planner" element={<Planner />} />
        <Route path="plans" element={<Plans />} />
        <Route path="plans/auto" element={<AutoPlans />} />
        <Route path="plans/:id" element={<PlanDetail />} />
        <Route path="profile" element={<Profile />} />
        <Route
          path="*"
          element={
            <div className="empty-state">
              <h2>{uiCopy.app042}</h2>
              <Button asChild>
                <Link to="/chat">{uiCopy.app043}</Link>
              </Button>
            </div>
          }
        />
      </Route>
    </Routes>
  );
}
