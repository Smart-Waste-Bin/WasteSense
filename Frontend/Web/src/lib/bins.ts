import { apiGet } from "./api"
import type { BinStatus } from "./theme"

// One bin from GET /api/bins (contract section 6). Only the fields the web app uses.
export type Bin = {
  id: string
  name: string
  location: { lat: number; lng: number }
  status: BinStatus
  maintenance: boolean
  is_physical: boolean
  last_fill: number | null
  last_battery: number | null
  last_seen_at: string | null
}

// The data of a bin_updated WebSocket event (contract section 7).
export type BinUpdate = Pick<Bin, "id" | "status" | "last_fill" | "last_battery" | "last_seen_at">

// Every screen that shows bins uses this key, so the map and the bins list stay the same.
export const BINS_QUERY_KEY = ["bins"] as const

// 100 is the largest page the API allows. We have 10 to 20 bins.
export async function fetchBins() {
  const page = await apiGet<{ items: Bin[]; total: number }>("/api/bins?size=100")
  return page.items
}

// The cached list with one bin changed. Returns null if the bin is not in the list.
export function applyBinUpdate(bins: Bin[], update: BinUpdate): Bin[] | null {
  if (!bins.some((bin) => bin.id === update.id)) return null
  return bins.map((bin) => (bin.id === update.id ? { ...bin, ...update } : bin))
}
