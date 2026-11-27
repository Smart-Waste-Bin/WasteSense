import { useEffect, useState } from "react"
import type { Map as LeafletMap } from "leaflet"
import { MapContainer, Marker, TileLayer, useMapEvents } from "react-leaflet"
import "leaflet/dist/leaflet.css"
import "@/components/map/bin-map.css"
import { getBinIcon } from "@/components/map/bin-marker-icon"
import { config } from "@/lib/config"

export type LatLng = { lat: number; lng: number }

type LocationPickerProps = {
  value: LatLng | null
  onChange: (value: LatLng) => void
}

function ClickToPlace({ onChange }: Pick<LocationPickerProps, "onChange">) {
  useMapEvents({
    click: (event) => onChange({ lat: event.latlng.lat, lng: event.latlng.lng }),
  })
  return null
}

export function LocationPicker({ value, onChange }: LocationPickerProps) {
  const [map, setMap] = useState<LeafletMap | null>(null)
  const [initialCenter] = useState<[number, number]>(() =>
    value ? [value.lat, value.lng] : config.mapCenter,
  )

  useEffect(() => {
    if (!map) return
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(map.getContainer())
    return () => observer.disconnect()
  }, [map])

  return (
    <div className="space-y-1.5">
      <div className="relative isolate h-56 overflow-hidden rounded-lg border">
        <MapContainer
          ref={setMap}
          center={initialCenter}
          zoom={value ? 17 : config.mapZoom}
          maxZoom={config.mapMaxZoom}
          className="h-full w-full cursor-crosshair"
        >
          <TileLayer url={config.tileUrl} attribution={config.tileAttribution} maxZoom={config.mapMaxZoom} />
          <ClickToPlace onChange={onChange} />
          {value && <Marker position={[value.lat, value.lng]} icon={getBinIcon("normal", null, true)} />}
        </MapContainer>
      </div>
      <p className="text-xs text-slate-500">
        {value
          ? `Lat ${value.lat.toFixed(6)}, Lng ${value.lng.toFixed(6)}`
          : "Click the map to drop a pin."}
      </p>
    </div>
  )
}
