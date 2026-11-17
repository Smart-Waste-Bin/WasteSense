import { useState, type CSSProperties } from "react"
import { Dashboard } from "./components/dashboard/dashboard"
import { Navbar } from "./components/dashboard/navbar"
import { Sidebar } from "./components/dashboard/sidebar"
import { Login } from "./components/auth/login"
import { SidebarInset, SidebarProvider } from "./components/ui/sidebar"

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(true)
  const [activePage, setActivePage] = useState("Dashboard")
  if (!isAuthenticated) return <Login onLogin={() => setIsAuthenticated(true)} />

  return (
    <SidebarProvider className="bg-[#f7f9fa] text-slate-900" style={{ "--sidebar-width": "260px" } as CSSProperties}>
      <Sidebar activePage={activePage} onNavigate={setActivePage} />
      <SidebarInset className="min-h-screen min-w-0 bg-[#f7f9fa]">
        <Navbar activePage={activePage} onSignOut={() => setIsAuthenticated(false)} />
        <Dashboard />
      </SidebarInset>
    </SidebarProvider>
  )
}

export default App
