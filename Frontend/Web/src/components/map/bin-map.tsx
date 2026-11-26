import { useEffect, useRef, useState, type ReactNode } from "react"
import type { FitBoundsOptions, LatLngBoundsExpression, Map as LeafletMap } from "leaflet"
import { MapContainer, Marker, TileLayer } from "react-leaflet"
import { Maximize } from "lucide-react"
import "leaflet/dist/leaflet.css"
import "./bin-map.css"
import { Button } from "@/components/ui/button"
import type { Bin } from "@/lib/bins"
import { config } from "@/lib/config"
import { BIN_STATUSES, STATUS_THEME, type BinStatus } from "@/lib/theme"
import { getBinIcon } from "./bin-marker-icon"

// Fitting to the bins never zooms in past 17, so a single bin is not shown too close.
const FIT_OPTIONS: FitBoundsOptions = { padding: [48, 48], maxZoom: 17 }

// The area that holds every bin, or null when there are none (the map then keeps the config centre).
function binBounds(bins: Bin[]): LatLngBoundsExpression | null {
  if (bins.length === 0) return null
  return bins.map((bin): [number, number] => [bin.location.lat, bin.location.lng])
}

type BinMapProps = {
  bins: Bin[]
  selectedBinId?: string | null
  onBinClick?: (bin: Bin) => void
  visibleStatuses?: readonly BinStatus[]
  height?: string | number
  center?: [number, number]
  zoom?: number
  // Extra layers from later tickets: route lines, stops, collector marker.
  children?: ReactNode
}

// The bins on an OpenStreetMap base map. Shows what it is given; it loads no data itself.
export function BinMap({
  bins,
  selectedBinId = null,
  onBinClick,
  visibleStatuses = BIN_STATUSES,
  height = "100%",
  center = config.mapCenter,
  zoom = config.mapZoom,
  children,
}: BinMapProps) {
  const [map, setMap] = useState<LeafletMap | null>(null)
  const hasFitted = useRef(false)

  const fitToBins = () => {
    const bounds = binBounds(bins)
    if (!map || !bounds) return
    map.invalidateSize() // measure the box first, or the zoom is worked out for the wrong size
    map.fitBounds(bounds, FIT_OPTIONS)
  }

  // Leaflet measures its box once. Tell it when the box changes size (page layout, sidebar toggle).
  useEffect(() => {
    if (!map) return
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(map.getContainer())
    return () => observer.disconnect()
  }, [map])

  // Fit once, when the bins first arrive. Live updates don't move the map.
  useEffect(() => {
    if (!map || bins.length === 0 || hasFitted.current) return
    hasFitted.current = true
    fitToBins()
  }, [map, bins])

  const visibleBins = bins.filter((bin) => visibleStatuses.includes(bin.status))

  return (
    <div className="relative isolate" style={{ height }}>
      <MapContainer ref={setMap} center={center} zoom={zoom} maxZoom={config.mapMaxZoom} className="h-full w-full">
        <TileLayer url={config.tileUrl} attribution={config.tileAttribution} maxZoom={config.mapMaxZoom} />
        {visibleBins.map((bin) => (
          <Marker
            key={bin.id}
            position={[bin.location.lat, bin.location.lng]}
            icon={getBinIcon(bin.status, bin.last_fill, bin.id === selectedBinId)}
            title={`${bin.name} (${bin.id}): ${STATUS_THEME[bin.status].label}`}
            zIndexOffset={bin.id === selectedBinId ? 1000 : 0}
            eventHandlers={{ click: () => onBinClick?.(bin) }}
          />
        ))}
        {children}
      </MapContainer>
      <Button
        variant="outline"
        size="sm"
        className="absolute top-20 left-2.5 z-[1000] bg-white shadow-sm"
        onClick={fitToBins}
        disabled={bins.length === 0}
      >
        <Maximize /> Fit all bins
      </Button>
    </div>
  )
}
