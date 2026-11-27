import { useState } from "react"
import { useSearchParams } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { BinMap } from "@/components/map/bin-map"
import { BinSidePanel } from "@/components/map/bin-side-panel"
import { MapLegend } from "@/components/map/map-legend"
import { StatusFilterMenu } from "@/components/map/status-filter-menu"
import { useLiveBins } from "@/hooks/use-live-bins"
import type { Bin } from "@/lib/bins"
import { BIN_STATUSES, type BinStatus } from "@/lib/theme"

// The ?status= URL value -> the statuses that are on.
// No param = all on. "" = all off. Case does not matter, so ?status=Due,Urgent works too.
function parseStatusParam(value: string | null): BinStatus[] {
  if (value === null) return [...BIN_STATUSES]
  const wanted = value.toLowerCase().split(",")
  return BIN_STATUSES.filter((status) => wanted.includes(status))
}

// The statuses that are on -> the ?status= URL value. null = all on, so the param is removed.
function toStatusParam(statuses: BinStatus[]): string | null {
  if (statuses.length === BIN_STATUSES.length) return null
  return BIN_STATUSES.filter((status) => statuses.includes(status)).join(",")
}

function toggleStatus(statuses: BinStatus[], status: BinStatus): BinStatus[] {
  return statuses.includes(status) ? statuses.filter((item) => item !== status) : [...statuses, status]
}

function countByStatus(bins: Bin[]): Record<BinStatus, number> {
  const counts = Object.fromEntries(BIN_STATUSES.map((status) => [status, 0])) as Record<BinStatus, number>
  for (const bin of bins) counts[bin.status] += 1
  return counts
}

export function LiveMap() {
  const { data: bins = [], isPending, isError, error, refetch } = useLiveBins()
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedBinId, setSelectedBinId] = useState<string | null>(null)

  const visibleStatuses = parseStatusParam(searchParams.get("status"))
  const selectedBin = bins.find((bin) => bin.id === selectedBinId && visibleStatuses.includes(bin.status))

  const handleToggle = (status: BinStatus) => {
    const next = toggleStatus(visibleStatuses, status)
    const param = toStatusParam(next)
    setSearchParams(
      (params) => {
        if (param === null) params.delete("status")
        else params.set("status", param)
        return params
      },
      { replace: true },
    )
    // A filter that hides the open bin closes its panel.
    const selected = bins.find((bin) => bin.id === selectedBinId)
    if (selected && !next.includes(selected.status)) setSelectedBinId(null)
  }

  return (
    <main className="flex h-[calc(100svh-84px)] min-w-0 flex-col gap-4 px-4 py-5 sm:px-6 lg:px-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-2xl font-bold tracking-tight text-slate-950">Live map</h2>
        <StatusFilterMenu selected={visibleStatuses} counts={countByStatus(bins)} onToggle={handleToggle} />
      </div>

      <div className="relative min-h-0 flex-1 overflow-hidden rounded-2xl border border-slate-200">
        <BinMap
          bins={bins}
          selectedBinId={selectedBin?.id ?? null}
          onBinClick={(bin) => setSelectedBinId(bin.id)}
          visibleStatuses={visibleStatuses}
        />

        <div className="absolute bottom-6 left-3 z-[1000]">
          <MapLegend />
        </div>

        {selectedBin && (
          <div className="absolute top-3 right-3 z-[1000]">
            <BinSidePanel bin={selectedBin} onClose={() => setSelectedBinId(null)} />
          </div>
        )}

        {(isPending || isError || bins.length === 0) && (
          <div className="absolute inset-0 z-[1000] flex items-center justify-center bg-white/60">
            <div className="flex flex-col items-center gap-3 rounded-2xl bg-white p-6 text-center shadow-lg">
              {isPending ? (
                <>
                  <Loader2 className="size-6 animate-spin text-emerald-700" />
                  <p className="text-sm font-semibold text-slate-600">Loading bins...</p>
                </>
              ) : isError ? (
                <>
                  <p className="text-sm font-semibold text-slate-800">Could not load bins.</p>
                  <p className="text-sm text-slate-500">{error.message}</p>
                  <Button onClick={() => void refetch()}>Retry</Button>
                </>
              ) : (
                <p className="text-sm font-semibold text-slate-600">No bins yet. Add your first bin.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </main>
  )
}
