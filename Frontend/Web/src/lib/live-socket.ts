import { getAccessToken, refreshSession } from "@/auth"
import { config } from "./config"

// One WebSocket to /ws for the whole app (contract section 7). Screens listen through useLiveEvents().

export type LiveEvent = { type: string; data: unknown; ts: string }

export type LiveListener = {
  onEvent: (event: LiveEvent) => void
  onReconnect: () => void
}

const RETRY_DELAYS_MS = [1000, 2000, 5000, 10000] // then every 10 s
const SILENCE_LIMIT_MS = 60000 // the server pings every 25 s
const BAD_TOKEN = 4401

const listeners = new Set<LiveListener>()
let socket: WebSocket | null = null
let attempt = 0
let hasConnected = false
let retryTimer: ReturnType<typeof setTimeout> | undefined
let silenceTimer: ReturnType<typeof setTimeout> | undefined

function resetSilenceTimer() {
  clearTimeout(silenceTimer)
  silenceTimer = setTimeout(() => socket?.close(), SILENCE_LIMIT_MS)
}

function scheduleRetry() {
  const delay = RETRY_DELAYS_MS[Math.min(attempt, RETRY_DELAYS_MS.length - 1)]
  attempt += 1
  retryTimer = setTimeout(connect, delay)
}

function connect() {
  const token = getAccessToken()
  if (!token || listeners.size === 0) return

  const current = new WebSocket(`${config.wsUrl}/ws?token=${encodeURIComponent(token)}`)
  socket = current

  current.onopen = () => {
    attempt = 0
    resetSilenceTimer()
    // Events sent while we were away are not replayed, so screens reload their data.
    if (hasConnected) listeners.forEach((listener) => listener.onReconnect())
    hasConnected = true
  }

  current.onmessage = (message: MessageEvent<string>) => {
    resetSilenceTimer()
    const event = JSON.parse(message.data) as LiveEvent
    if (event.type === "ping") return
    listeners.forEach((listener) => listener.onEvent(event))
  }

  current.onclose = (closed) => {
    clearTimeout(silenceTimer)
    if (socket !== current) return // closed on purpose
    socket = null
    if (closed.code === BAD_TOKEN) {
      // Expired access token: refresh once and reconnect. If refresh fails, the user must log in again.
      refreshSession().then(connect, () => undefined)
      return
    }
    scheduleRetry()
  }
}

function disconnect() {
  clearTimeout(retryTimer)
  clearTimeout(silenceTimer)
  const current = socket
  socket = null
  attempt = 0
  hasConnected = false
  current?.close()
}

// Start listening. Returns the function that stops. The socket is open while anyone listens.
export function listen(listener: LiveListener) {
  listeners.add(listener)
  if (!socket && listeners.size === 1) connect()
  return () => {
    listeners.delete(listener)
    if (listeners.size === 0) disconnect()
  }
}
