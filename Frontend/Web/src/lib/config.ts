// All settings from the environment (Frontend/Web/.env.example), read in one place.

const env = import.meta.env

function readNumber(value: string | undefined, fallback: number) {
  const number = Number(value)
  return value && Number.isFinite(number) ? number : fallback
}

export function readLatLng(value: string | undefined, fallback: [number, number]): [number, number] {
  const parts = (value ?? "").split(",").map((part) => Number(part.trim()))
  if (parts.length !== 2 || parts.some((part) => !Number.isFinite(part))) return fallback
  return [parts[0], parts[1]]
}

const apiUrl = (env.VITE_API_URL as string | undefined)?.replace(/\/$/, "") || "http://localhost:8000"

export const config = {
  apiUrl,
  wsUrl: apiUrl.replace(/^http/, "ws"),
  tileUrl: (env.VITE_TILE_URL as string | undefined) || "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
  tileAttribution:
    (env.VITE_TILE_ATTRIBUTION as string | undefined) ||
    '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  mapCenter: readLatLng(env.VITE_MAP_CENTER as string | undefined, [6.6885, -1.6244]),
  mapZoom: readNumber(env.VITE_MAP_ZOOM as string | undefined, 13),
  mapMaxZoom: readNumber(env.VITE_MAP_MAX_ZOOM as string | undefined, 19),
}
