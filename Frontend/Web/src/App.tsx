import { useEffect, useState, type CSSProperties } from "react";
import { Dashboard } from "./pages/dashboard";
import { Navbar } from "./components/dashboard/navbar";
import { Sidebar } from "./components/dashboard/sidebar";
import { Settings } from "./pages/settings";
import { LiveMap } from "./pages/live-map";
import { Login } from "./components/auth/login";
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar";
import { getCurrentUser, logout, type AuthUser } from "./auth";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";

const pagePaths = {
  Overview: "/",
  "Live Map": "/live-map",
  Bins: "/bins",
  Alerts: "/alerts",
  Routes: "/routes",
  "Live Tracking": "/live-tracking",
  Collectors: "/collectors",
  Settings: "/settings",
} as const;

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();
  const activePage =
    Object.entries(pagePaths).find(([, path]) => path === location.pathname)?.[0] ??
    "Overview";

  useEffect(() => {
    getCurrentUser()
      .then(setUser)
      .finally(() => setIsCheckingSession(false));
  }, []);

  if (isCheckingSession) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f5f5f5]">
        <p className="text-sm font-semibold text-slate-500">
          Opening your dashboard...
        </p>
      </div>
    );
  }

  if (!user) return <Login onLogin={setUser} />;

  const handleSignOut = async () => {
    await logout();
    setUser(null);
  };

  const handleNavigate = (page: string) => {
    const path = Object.entries(pagePaths).find(([label]) => label === page)?.[1];
    if (path) navigate(path);
  };

  return (
    <SidebarProvider
      className="bg-[#f7f9fa] text-slate-900"
      style={{ "--sidebar-width": "260px" } as CSSProperties}
    >
      <Sidebar activePage={activePage} onNavigate={handleNavigate} />
      <SidebarInset className="min-h-screen min-w-0 bg-[#f7f9fa]">
        <Navbar
          activePage={activePage}
          onNavigate={handleNavigate}
          onSignOut={handleSignOut}
          user={user}
        />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/live-map" element={<LiveMap />} />
          <Route path="/bins" element={<Dashboard />} />
          <Route path="/alerts" element={<Dashboard />} />
          <Route path="/routes" element={<Dashboard />} />
          <Route path="/live-tracking" element={<Dashboard />} />
          <Route path="/collectors" element={<Dashboard />} />
          <Route
            path="/settings"
            element={<Settings user={user} onProfileUpdate={setUser} />}
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </SidebarInset>
    </SidebarProvider>
  );
}

export default App;
