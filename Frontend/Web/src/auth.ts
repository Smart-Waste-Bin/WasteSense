import { config } from "./lib/config"

export type AuthUser = {
  id: string
  name: string
  email: string
  phone: string | null
  role: string
  photo_url?: string | null
}

type LoginResponse = {
  access_token: string
  token_type: string
  expires_in: number
  refresh_token: string
  user: AuthUser
}

type ErrorResponse = {
  error?: {
    code?: string
    message?: string
  }
}

const API_URL = config.apiUrl
const ACCESS_TOKEN_KEY = "wastesense.access_token"
const REFRESH_TOKEN_KEY = "wastesense.refresh_token"

function readStoredToken(key: string) {
  return localStorage.getItem(key) ?? sessionStorage.getItem(key)
}

function clearStoredTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  sessionStorage.removeItem(ACCESS_TOKEN_KEY)
  sessionStorage.removeItem(REFRESH_TOKEN_KEY)
}

function storeTokens(accessToken: string, refreshToken: string, rememberMe: boolean) {
  clearStoredTokens()
  const storage = rememberMe ? localStorage : sessionStorage
  storage.setItem(ACCESS_TOKEN_KEY, accessToken)
  storage.setItem(REFRESH_TOKEN_KEY, refreshToken)
}

export function getAccessToken() {
  return readStoredToken(ACCESS_TOKEN_KEY)
}

export async function readApiError(response: Response) {
  try {
    const data = (await response.json()) as ErrorResponse
    return data.error?.message || "The request could not be completed."
  } catch {
    return "The server could not be reached."
  }
}

async function apiRequest(path: string, init: RequestInit = {}) {
  const headers = new Headers(init.headers)
  if (!(init.body instanceof FormData) && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json")
  }
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers,
  })
  if (!response.ok) throw new Error(await readApiError(response))
  return response
}

export async function login(loginName: string, password: string, rememberMe: boolean) {
  const response = await apiRequest("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ login: loginName, password }),
  })
  const data = (await response.json()) as LoginResponse
  storeTokens(data.access_token, data.refresh_token, rememberMe)
  return data.user
}

export async function refreshSession() {
  const refreshToken = readStoredToken(REFRESH_TOKEN_KEY)
  const response = await apiRequest("/api/auth/refresh", {
    method: "POST",
    body: JSON.stringify({ refresh_token: refreshToken }),
  })
  const data = (await response.json()) as LoginResponse
  const rememberMe = localStorage.getItem(REFRESH_TOKEN_KEY) !== null
  storeTokens(data.access_token, data.refresh_token, rememberMe)
  return data.user
}

export async function getCurrentUser() {
  const accessToken = getAccessToken()
  if (!accessToken) return null
  try {
    const response = await apiRequest("/api/me", {
      headers: { Authorization: `Bearer ${accessToken}` },
    })
    return (await response.json()) as AuthUser
  } catch {
    try {
      return await refreshSession()
    } catch {
      clearStoredTokens()
      return null
    }
  }
}

export async function updateCurrentUser(profile: Pick<AuthUser, "name" | "phone">) {
  const accessToken = getAccessToken()
  if (!accessToken) throw new Error("Your session has expired. Please sign in again.")
  const response = await apiRequest("/api/me", {
    method: "PATCH",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(profile),
  })
  return (await response.json()) as AuthUser
}

export async function changeCurrentUserPassword(passwords: {
  current_password: string
  new_password: string
  confirm_password: string
}) {
  const accessToken = getAccessToken()
  if (!accessToken) throw new Error("Your session has expired. Please sign in again.")
  const response = await apiRequest("/api/me/password", {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify(passwords),
  })
  const data = (await response.json()) as LoginResponse
  const rememberMe = localStorage.getItem(REFRESH_TOKEN_KEY) !== null
  storeTokens(data.access_token, data.refresh_token, rememberMe)
  return data.user
}

export async function uploadCurrentUserPhoto(photo: File) {
  const accessToken = getAccessToken()
  if (!accessToken) throw new Error("Your session has expired. Please sign in again.")
  const formData = new FormData()
  formData.append("photo", photo)
  const response = await apiRequest("/api/me/photo", {
    method: "PUT",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: formData,
  })
  return (await response.json()) as AuthUser
}

export async function removeCurrentUserPhoto() {
  const accessToken = getAccessToken()
  if (!accessToken) throw new Error("Your session has expired. Please sign in again.")
  const response = await apiRequest("/api/me/photo", {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  })
  return (await response.json()) as AuthUser
}

export function getPhotoUrl(photoUrl: string | null | undefined) {
  return photoUrl ? new URL(photoUrl, `${API_URL}/`).toString() : null
}

export async function logout() {
  const accessToken = getAccessToken()
  const refreshToken = readStoredToken(REFRESH_TOKEN_KEY)
  try {
    await apiRequest("/api/auth/logout", {
      method: "POST",
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
      body: JSON.stringify({ refresh_token: refreshToken, all_devices: false }),
    })
  } catch {
    // Clear the browser session even if the server is temporarily unavailable.
  } finally {
    clearStoredTokens()
  }
}
