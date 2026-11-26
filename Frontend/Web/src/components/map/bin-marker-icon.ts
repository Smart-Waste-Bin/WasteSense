import { createElement } from "react"
import { renderToStaticMarkup } from "react-dom/server"
import L from "leaflet"
import { STATUS_THEME, type BinStatus } from "@/lib/theme"

export function fillLabel(fill: number | null) {
  return fill === null ? "—" : `${Math.round(fill)}%`
}

// Offline and Maintenance show their icon (the last fill may be old), the rest show the fill.
export function markerContent(status: BinStatus, fill: number | null) {
  const { icon } = STATUS_THEME[status]
  return icon ? renderToStaticMarkup(createElement(icon, { size: 14, strokeWidth: 2.5 })) : fillLabel(fill)
}

// One icon per (status, fill, selected), so markers don't flicker when data comes in.
const cache = new Map<string, L.DivIcon>()

export function getBinIcon(status: BinStatus, fill: number | null, selected: boolean) {
  const rounded = fill === null ? null : Math.round(fill)
  const key = `${status}|${rounded}|${selected}`
  let icon = cache.get(key)
  if (!icon) {
    const size = selected ? 44 : 36
    icon = L.divIcon({
      className: "",
      html: `<div class="bin-marker${selected ? " bin-marker--selected" : ""}" style="--bin-color: ${STATUS_THEME[status].color}">${markerContent(status, rounded)}</div>`,
      iconSize: [size, size],
      iconAnchor: [size / 2, size / 2],
    })
    cache.set(key, icon)
  }
  return icon
}
