import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip"
import type { Bin } from "@/lib/bins"
import { formatRelativeTime } from "@/lib/relative-time"
import { STATUS_THEME } from "@/lib/theme"
import { fillLabel } from "./bin-marker-icon"
import { StatusDot } from "./status-dot"

// Turn on when route planning (OPS-01) is ready. Enables "Add to route" on the live map.
const ROUTE_PLANNING_ENABLED = false

// The current time, updated every 30 s so "2 min ago" stays right.
function useNow() {
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 30000)
    return () => clearInterval(timer)
  }, [])
  return now
}

const LINK_CLASS =
  "inline-flex h-9 flex-1 items-center justify-center rounded-md border border-transparent text-sm font-medium"

type BinSidePanelProps = {
  bin: Bin
  onClose: () => void
}

export function BinSidePanel({ bin, onClose }: BinSidePanelProps) {
  const now = useNow()
  const theme = STATUS_THEME[bin.status]
  const fill = Math.min(100, Math.max(0, bin.last_fill ?? 0))

  useEffect(() => {
    const closeOnEsc = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose()
    }
    window.addEventListener("keydown", closeOnEsc)
    return () => window.removeEventListener("keydown", closeOnEsc)
  }, [onClose])

  return (
    <aside
      aria-label={`Bin ${bin.id}`}
      className="flex w-80 flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-lg"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-bold text-slate-950">{bin.name}</h3>
          <p className="text-sm text-slate-500">{bin.id}</p>
        </div>
        <Button variant="ghost" size="icon-sm" aria-label="Close" onClick={onClose}>
          <X />
        </Button>
      </div>

      <span
        className="inline-flex w-fit items-center gap-2 rounded-full px-3 py-1 text-sm font-semibold"
        style={{ backgroundColor: `${theme.color}1f`, color: theme.color }}
      >
        <StatusDot status={bin.status} />
        {theme.label}
      </span>

      <div>
        <div className="mb-1 flex justify-between text-sm">
          <span className="text-slate-500">Fill level</span>
          <span className="font-semibold text-slate-900">{fillLabel(bin.last_fill)}</span>
        </div>
        <div
          role="progressbar"
          aria-label="Fill level"
          aria-valuenow={bin.last_fill ?? undefined}
          aria-valuemin={0}
          aria-valuemax={100}
          className="h-2 overflow-hidden rounded-full bg-slate-100"
        >
          <div className="h-full rounded-full" style={{ width: `${fill}%`, backgroundColor: theme.color }} />
        </div>
      </div>

      <dl className="grid grid-cols-2 gap-y-2 text-sm">
        <dt className="text-slate-500">Battery</dt>
        <dd className="text-right font-semibold text-slate-900">
          {bin.last_battery === null ? "—" : `${Math.round(bin.last_battery)}%`}
        </dd>
        <dt className="text-slate-500">Last update</dt>
        <dd className="text-right font-semibold text-slate-900">{formatRelativeTime(bin.last_seen_at, now)}</dd>
      </dl>

      <div className="flex gap-2">
        <Link to={`/bins/${bin.id}`} className={`${LINK_CLASS} border-slate-200 text-slate-700 hover:bg-slate-50`}>
          View details
        </Link>
        {ROUTE_PLANNING_ENABLED ? (
          <Link to={`/routes/new?add=${bin.id}`} className={`${LINK_CLASS} bg-primary text-primary-foreground hover:bg-primary/80`}>
            Add to route
          </Link>
        ) : (
          <Tooltip>
            <TooltipTrigger render={<span tabIndex={0} className="flex-1" />}>
              <Button className="w-full" disabled>
                Add to route
              </Button>
            </TooltipTrigger>
            <TooltipContent>Available when route planning is ready</TooltipContent>
          </Tooltip>
        )}
      </div>
    </aside>
  )
}
