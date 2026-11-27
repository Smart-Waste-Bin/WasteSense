import { useEffect, useEffectEvent } from "react"
import { listen, type LiveEvent } from "@/lib/live-socket"

// Live events from the backend WebSocket. All screens share one connection.
// onReconnect runs after the socket comes back, so the screen can reload missed data.
export function useLiveEvents(onEvent: (event: LiveEvent) => void, onReconnect: () => void) {
  const handleEvent = useEffectEvent(onEvent)
  const handleReconnect = useEffectEvent(onReconnect)

  useEffect(
    () =>
      listen({
        onEvent: (event) => handleEvent(event),
        onReconnect: () => handleReconnect(),
      }),
    [],
  )
}
