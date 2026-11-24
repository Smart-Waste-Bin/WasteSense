import { Menu } from "@base-ui/react/menu";
import { ChevronDown, LogOut, Settings } from "lucide-react";
import { getPhotoUrl, type AuthUser } from "@/auth";
import { Button } from "../ui/button";

type ProfileMenuProps = {
  onNavigate: (page: string) => void;
  onSignOut: () => void;
  user: AuthUser;
};

function ProfileMenu({ onNavigate, onSignOut, user }: ProfileMenuProps) {
  const photoUrl = getPhotoUrl(user.photo_url);

  return (
    <Menu.Root>
      <Menu.Trigger
        render={
          <Button
            variant="ghost"
            aria-label="Open profile menu"
            className="h-auto gap-2 p-0 hover:bg-transparent sm:gap-3"
          />
        }
      >
        <span className="flex size-9 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-sm font-bold text-emerald-700">
          {photoUrl ? (
            <img src={photoUrl} alt="" className="size-full rounded-full object-cover" />
          ) : (
            user.name.split(" ").map((part) => part[0]).join("").slice(0, 2).toUpperCase()
          )}
        </span>
        <span className="hidden text-left sm:block">
          <span className="block text-sm font-bold">{user.name}</span>
          <span className="block text-xs capitalize text-slate-400">{user.role}</span>
        </span>
        <ChevronDown size={16} className="text-slate-400" />
      </Menu.Trigger>
      <Menu.Portal>
        <Menu.Positioner side="bottom" align="end" sideOffset={8}>
          <Menu.Popup className="z-50 min-w-48 rounded-xl border border-slate-200 bg-white p-1.5 text-sm text-slate-700 shadow-lg outline-none data-ending-style:scale-95 data-ending-style:opacity-0 data-starting-style:scale-95 data-starting-style:opacity-0">
            <Menu.Item
              onClick={() => onNavigate("Settings")}
              className="flex cursor-default items-center gap-2 rounded-lg px-3 py-2.5 outline-none data-highlighted:bg-emerald-50 data-highlighted:text-emerald-700"
            >
              <Settings size={16} />
              Settings
            </Menu.Item>
            <Menu.Separator className="my-1 h-px bg-slate-100" />
            <Menu.Item
              onClick={onSignOut}
              className="flex cursor-default items-center gap-2 rounded-lg px-3 py-2.5 text-red-600 outline-none data-highlighted:bg-red-50 data-highlighted:text-red-700"
            >
              <LogOut size={16} />
              Log out
            </Menu.Item>
          </Menu.Popup>
        </Menu.Positioner>
      </Menu.Portal>
    </Menu.Root>
  );
}

export { ProfileMenu };
