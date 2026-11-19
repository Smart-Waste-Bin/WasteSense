import { Bell, ChevronDown, Search } from "lucide-react";
import { Button } from "../ui/button";
import { Separator } from "../ui/separator";
import { SidebarTrigger } from "../ui/sidebar";
import { Input } from "../ui/input";

type NavbarProps = { activePage: string; onSignOut: () => void };

function Navbar({ activePage, onSignOut }: NavbarProps) {
  return (
    <header className="sticky top-0 z-20 flex h-[84px] w-full shrink-0 items-center justify-between border-b border-slate-200 bg-white/90 px-5 backdrop-blur-md sm:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger className="size-9 shrink-0 text-slate-500" />
        <Separator orientation="vertical" className="hidden h-6 sm:block" />
        <div className="min-w-0 flex-1">
          <Search className="absolute top-7 mx-2 text-gray-400" />
          <Input
            placeholder="Search bins, routes, collectors..."
            aria-label={`${activePage} search`}
            className="h-8 w-220 max-w-[37.5rem] p-4 pl-11"
          />
        </div>
      </div>
      <div className="ml-4 flex shrink-0 items-center gap-2 sm:gap-4">
        <Button
          variant="ghost"
          size="icon"
          className="relative rounded-xl text-slate-400"
        >
          <Bell size={20} />
          <span className="absolute right-1.5 top-1.5 size-2 rounded-full bg-emerald-500 ring-2 ring-white" />
        </Button>
        <div className="hidden h-8 w-px bg-slate-200 sm:block" />
        <Button
          variant="ghost"
          onClick={onSignOut}
          className="h-auto gap-2 p-0 hover:bg-transparent sm:gap-3"
        >
          <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700">
            JD
          </span>
          <span className="hidden text-left sm:block">
            <span className="block text-sm font-bold">Jordan Davis</span>
            <span className="block text-xs text-slate-400">Administrator</span>
          </span>
          <ChevronDown size={16} className="text-slate-400" />
        </Button>
      </div>
    </header>
  );
}

export { Navbar };
