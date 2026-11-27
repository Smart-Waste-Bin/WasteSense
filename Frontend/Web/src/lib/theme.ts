import { Wrench, WifiOff, type LucideIcon } from "lucide-react"

// Bin statuses come from the backend (contract section 6). The frontend never works them out.
export const BIN_STATUSES = ["normal", "filling", "due", "urgent", "offline", "maintenance"] as const

export type BinStatus = (typeof BIN_STATUSES)[number]

type StatusTheme = {
  label: string
  color: string
  icon: LucideIcon | null
}

export const STATUS_THEME: Record<BinStatus, StatusTheme> = {
  normal: { label: "Normal", color: "#639922", icon: null },
  filling: { label: "Filling", color: "#EF9F27", icon: null },
  due: { label: "Due", color: "#D85A30", icon: null },
  urgent: { label: "Urgent", color: "#E24B4A", icon: null },
  offline: { label: "Offline", color: "#888780", icon: WifiOff },
  maintenance: { label: "Maintenance", color: "#5F5E5A", icon: Wrench },
}
