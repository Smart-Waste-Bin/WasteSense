import { getAccessToken, readApiError, refreshSession } from "@/auth"
import { config } from "./config"

function send(path: string) {
  const token = getAccessToken()
  return fetch(`${config.apiUrl}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

// GET a JSON endpoint as the logged-in user. An expired access token is refreshed once.
export async function apiGet<T>(path: string): Promise<T> {
  let response = await send(path)
  if (response.status === 401) {
    await refreshSession()
    response = await send(path)
  }
  if (!response.ok) throw new Error(await readApiError(response))
  return (await response.json()) as T
}
