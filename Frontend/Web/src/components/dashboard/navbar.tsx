import * as React from "react";
import { Bell } from "lucide-react";
import { Button } from "../ui/button";
import { Separator } from "../ui/separator";
import { SidebarTrigger } from "../ui/sidebar";
import { SearchBar, type SearchSuggestion } from "../ui/search-bar";
import type { AuthUser } from "@/auth";
import { ProfileMenu } from "./profile-menu";

type NavbarProps = {
  activePage: string;
  onNavigate: (page: string) => void;
  onSignOut: () => void;
  user: AuthUser;
};

function Navbar({ activePage, onNavigate, onSignOut, user }: NavbarProps) {
  const [searchQuery, setSearchQuery] = React.useState("");
  const searchSuggestions: SearchSuggestion[] = [
    { id: "1", label: "Library entrance", description: "Bin" },
    { id: "2", label: "Science block", description: "Bin" },
    { id: "3", label: "Student center", description: "Bin" },
    { id: "4", label: "Main campus route", description: "Route" },
    { id: "5", label: "Peter Owusu", description: "Collector" },
  ];

  return (
    <header className="sticky top-0 z-20 flex h-[84px] w-full shrink-0 items-center justify-between border-b border-slate-200 bg-white/90 px-5 backdrop-blur-md sm:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <SidebarTrigger className="size-9 shrink-0 text-slate-500" />
        <Separator orientation="vertical" className="hidden h-6 sm:block" />
        <div className="w-[min(37.5rem,50vw)] min-w-0">
          <SearchBar
            value={searchQuery}
            onChange={setSearchQuery}
            placeholder="Search bins, routes, collectors..."
            ariaLabel={`${activePage} search`}
            suggestions={searchSuggestions}
            onSelect={(suggestion) => setSearchQuery(suggestion.label)}
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
        <ProfileMenu
          user={user}
          onNavigate={onNavigate}
          onSignOut={onSignOut}
        />
      </div>
    </header>
  );
}

export { Navbar };
