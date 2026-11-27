import { STATUS_THEME, type BinStatus } from "@/lib/theme"

// A status colour, with the status icon on Offline and Maintenance.
export function StatusDot({ status }: { status: BinStatus }) {
  const { color, icon: Icon } = STATUS_THEME[status]
  return (
    <span
      className="inline-flex size-4 shrink-0 items-center justify-center rounded-full text-white"
      style={{ backgroundColor: color }}
      aria-hidden="true"
    >
      {Icon && <Icon size={10} strokeWidth={3} />}
    </span>
  )
}
