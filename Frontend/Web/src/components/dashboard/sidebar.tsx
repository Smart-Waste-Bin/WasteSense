import { CircleHelp, LayoutDashboard, PackageCheck, Recycle, Settings, Truck, Users } from "lucide-react"
import { Logo } from "@/components/brand/logo"
import {
  Sidebar as ShadcnSidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuBadge,
  SidebarMenuButton,
  SidebarMenuItem,
  useSidebar,
} from "@/components/ui/sidebar"

const navigation = [
  { label: "Dashboard", icon: LayoutDashboard },
  { label: "Smart Bins", icon: PackageCheck, badge: "24" },
  { label: "Collection routes", icon: Truck },
  { label: "Analytics", icon: Recycle },
]

type SidebarProps = {
  activePage: string
  onNavigate: (page: string) => void
}

function NavigationItem({
  label,
  icon: Icon,
  badge,
  activePage,
  onNavigate,
}: {
  label: string
  icon: typeof LayoutDashboard
  badge?: string
  activePage: string
  onNavigate: (page: string) => void
}) {
  const { isMobile, setOpenMobile } = useSidebar()

  const handleNavigate = () => {
    onNavigate(label)
    if (isMobile) setOpenMobile(false)
  }

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        isActive={activePage === label}
        tooltip={label}
        onClick={handleNavigate}
        className="h-auto rounded-xl px-3 py-3 text-sm font-semibold data-active:bg-emerald-50 data-active:text-emerald-700 data-active:hover:bg-emerald-50"
      >
        <Icon size={19} strokeWidth={activePage === label ? 2.4 : 2} />
        <span>{label}</span>
      </SidebarMenuButton>
      {badge && <SidebarMenuBadge className="right-3 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">{badge}</SidebarMenuBadge>}
    </SidebarMenuItem>
  )
}

function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <ShadcnSidebar className="border-slate-200 bg-white" collapsible="icon">
      <SidebarHeader className="px-5 py-7">
        <Logo />
      </SidebarHeader>
      <SidebarContent className="px-3">
        <SidebarGroup className="p-0">
          <SidebarGroupLabel className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Workspace</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation.map((item) => <NavigationItem key={item.label} {...item} activePage={activePage} onNavigate={onNavigate} />)}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup className="mt-7 p-0">
          <SidebarGroupLabel className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">Support</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              <SidebarMenuItem><SidebarMenuButton className="h-auto rounded-xl px-3 py-3 text-sm font-semibold text-slate-500"><CircleHelp size={19} /><span>Help center</span></SidebarMenuButton></SidebarMenuItem>
              <SidebarMenuItem><SidebarMenuButton className="h-auto rounded-xl px-3 py-3 text-sm font-semibold text-slate-500"><Settings size={19} /><span>Settings</span></SidebarMenuButton></SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-5 group-data-[collapsible=icon]:p-2">
        <div className="rounded-2xl bg-slate-50 p-4 group-data-[collapsible=icon]:bg-transparent group-data-[collapsible=icon]:p-0">
          <div className="mb-3 flex size-9 items-center justify-center rounded-full bg-emerald-100 text-emerald-700 group-data-[collapsible=icon]:mb-0"><Users size={18} /></div>
          <p className="text-sm font-bold group-data-[collapsible=icon]:hidden">City operations</p>
          <p className="mt-1 text-xs leading-5 text-slate-500 group-data-[collapsible=icon]:hidden">12 team members online</p>
        </div>
      </SidebarFooter>
    </ShadcnSidebar>
  )
}

export { Sidebar }
