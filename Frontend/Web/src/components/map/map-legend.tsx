import { BIN_STATUSES, STATUS_THEME } from "@/lib/theme"
import { StatusDot } from "./status-dot"

export function MapLegend() {
  return (
    <section aria-label="Map legend" className="rounded-xl border border-slate-200 bg-white/95 p-3 shadow-sm">
      <h3 className="mb-2 text-xs font-bold tracking-wide text-slate-500 uppercase">Legend</h3>
      <ul className="space-y-1.5">
        {BIN_STATUSES.map((status) => (
          <li key={status} className="flex items-center gap-2 text-sm text-slate-700">
            <StatusDot status={status} />
            {STATUS_THEME[status].label}
          </li>
        ))}
      </ul>
    </section>
  )
}
