import { useEffect, useState, type CSSProperties } from "react";
import { Dashboard } from "./pages/dashboard";
import { Navbar } from "./components/dashboard/navbar";
import { Sidebar } from "./components/dashboard/sidebar";
import { Settings } from "./pages/settings";
import { Login } from "./components/auth/login";
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar";
import { getCurrentUser, logout, type AuthUser } from "./auth";

function App() {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isCheckingSession, setIsCheckingSession] = useState(true);
  const [activePage, setActivePage] = useState("Overview");

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

  return (
    <SidebarProvider
      className="bg-[#f7f9fa] text-slate-900"
      style={{ "--sidebar-width": "260px" } as CSSProperties}
    >
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <SidebarInset className="min-h-screen min-w-0 bg-[#f7f9fa]">
        <Navbar
          activePage={activePage}
          onNavigate={setActivePage}
          onSignOut={handleSignOut}
          user={user}
        />
        {activePage === "Settings" ? (
          <Settings user={user} onProfileUpdate={setUser} />
        ) : (
          <Dashboard />
        )}
      </SidebarInset>
    </SidebarProvider>
  );
}

export default App;
