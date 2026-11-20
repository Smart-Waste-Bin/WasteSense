import {
  Users,
  LayoutDashboard,
  Map,
  TriangleExclamationPoint,
  RadioTower,
  Trash,
  Route,
  CircleHelp,
  Settings,
} from "lucide-react";

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
} from "@/components/ui/sidebar";
import Logo from "@/assets/logo.jpg";

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Live Map", icon: Map, badge: "24" },
  { label: "Bins", icon: Trash },
  { label: "Alerts", icon: TriangleExclamationPoint, badge: "3" },
  { label: "Routes", icon: Route },
  { label: "Live Tracking", icon: RadioTower },
  { label: "Collectors", icon: Users },
];

type SidebarProps = {
  activePage: string;
  onNavigate: (page: string) => void;
};

function NavigationItem({
  label,
  icon: Icon,
  badge,
  activePage,
  onNavigate,
}: {
  label: string;
  icon: typeof LayoutDashboard;
  badge?: string;
  activePage: string;
  onNavigate: (page: string) => void;
}) {
  const { isMobile, setOpenMobile } = useSidebar();

  const handleNavigate = () => {
    onNavigate(label);
    if (isMobile) setOpenMobile(false);
  };

  return (
    <SidebarMenuItem>
      <SidebarMenuButton
        isActive={activePage === label}
        tooltip={label}
        onClick={handleNavigate}
        className="h-auto rounded-xl px-3 py-3 text-sm font-semibold data-active:bg-emerald-50 data-active:text-emerald-700 data-active:hover:bg-emerald-50"
      >
        <Icon
          size={19}
          strokeWidth={activePage === label ? 2.4 : 2}
          className="shrink-0"
        />
        <span className="font-sans ">{label}</span>
      </SidebarMenuButton>
      {badge && (
        <SidebarMenuBadge className="right-3 rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-slate-500">
          {badge}
        </SidebarMenuBadge>
      )}
    </SidebarMenuItem>
  );
}

function Sidebar({ activePage, onNavigate }: SidebarProps) {
  return (
    <ShadcnSidebar className="border-slate-200 bg-white" collapsible="icon">
      <SidebarHeader className="px-5 py-7 group-data-[collapsible=icon]:px-2">
        <div className="flex items-center justify-start gap-2 group-data-[collapsible=icon]:justify-center">
          <img src={Logo} alt="Logo" className="h-8 w-8 shrink-0 rounded-sm" />
          <h1 className="text-lg font-bold group-data-[collapsible=icon]:hidden font-logo tracking-tight text-slate-950">
            Smart<span className="text-emerald-700">Bin</span>
          </h1>
        </div>
      </SidebarHeader>
      <SidebarContent className="px-3">
        <SidebarGroup className="p-0">
          <SidebarGroupLabel className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
            MONITOR
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation.slice(0, 4).map((item) => (
                <NavigationItem
                  key={item.label}
                  {...item}
                  activePage={activePage}
                  onNavigate={onNavigate}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup className="mt-7 p-0">
          <SidebarGroupLabel className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
            OPERATE
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              {navigation.slice(4).map((item) => (
                <NavigationItem
                  key={item.label}
                  {...item}
                  activePage={activePage}
                  onNavigate={onNavigate}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
        <SidebarGroup className="mt-7 p-0">
          <SidebarGroupLabel className="px-3 text-[10px] font-bold uppercase tracking-[0.18em] text-slate-400">
            Support
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="gap-1">
              <SidebarMenuItem>
                <SidebarMenuButton className="h-auto rounded-xl px-3 py-3 text-sm font-semibold text-slate-500">
                  <CircleHelp size={19} />
                  <span>Help center</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
              <SidebarMenuItem>
                <SidebarMenuButton className="h-auto rounded-xl px-3 py-3 text-sm font-semibold text-slate-500">
                  <Settings size={19} />
                  <span>Settings</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-5 group-data-[collapsible=icon]:p-2">
        <div className="rounded-2xl bg-slate-50 p-4 group-data-[collapsible=icon]:bg-transparent group-data-[collapsible=icon]:p-0">
          <h6 className="mt-1 leading-5 group-data-[collapsible=icon]:hidden font-bold">
            All systems live
          </h6>
          <p className="text-xs leading-5 text-slate-500 group-data-[collapsible=icon]:hidden">
            9 of 10 sensors reporting
          </p>
        </div>
      </SidebarFooter>
    </ShadcnSidebar>
  );
}

export { Sidebar };
