import { ChevronDown } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import { BIN_STATUSES, STATUS_THEME, type BinStatus } from "@/lib/theme"
import { StatusDot } from "./status-dot"

type StatusFilterMenuProps = {
  selected: BinStatus[]
  counts: Record<BinStatus, number>
  onToggle: (status: BinStatus) => void
}

function buttonLabel(selected: BinStatus[]) {
  if (selected.length === BIN_STATUSES.length) return "All statuses"
  if (selected.length === 0) return "No statuses"
  if (selected.length === 1) return STATUS_THEME[selected[0]].label
  return `${selected.length} statuses`
}

// A dropdown with a tick box per status. The menu stays open so several can be picked.
export function StatusFilterMenu({ selected, counts, onToggle }: StatusFilterMenuProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger render={<Button variant="outline" aria-label="Filter bins by status" />}>
        {buttonLabel(selected)}
        <ChevronDown />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-52">
        {BIN_STATUSES.map((status) => (
          <DropdownMenuCheckboxItem
            key={status}
            checked={selected.includes(status)}
            onCheckedChange={() => onToggle(status)}
          >
            <StatusDot status={status} />
            {STATUS_THEME[status].label}
            <span className="ml-auto text-xs text-slate-500">{counts[status]}</span>
          </DropdownMenuCheckboxItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
