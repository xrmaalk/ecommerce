import { apiBase, type Post } from "./api"

export type ArchiveReader = {
  id: number
  email: string
  first_name: string
  last_name: string
  date_joined: string
}

export type ReaderRegistration = {
  email: string
  first_name: string
  last_name: string
  password: string
  password_confirm: string
}

export type ArchiveComment = {
  id: number
  author_name: string
  body: string
  created_at: string
  is_mine: boolean
}

export type PostEngagement = {
  like_count: number
  liked: boolean
  comment_count: number
  comments: ArchiveComment[]
}

export type SubscriptionState = {
  subscribed: boolean
  subscribed_at: string | null
}

export type NotificationState = {
  subscribed: boolean
  unread_count: number
  results: Post[]
}

export class ReaderApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

let csrfToken: string | null = null

async function ensureCsrfToken(force = false) {
  if (csrfToken && !force) return csrfToken
  const response = await fetch(`${apiBase}/auth/csrf/`, {
    credentials: "include",
    headers: { Accept: "application/json" },
  })
  if (!response.ok) throw new ReaderApiError(response.status, "Could not start a secure session.")
  const data = (await response.json()) as { csrf_token: string }
  csrfToken = data.csrf_token
  return csrfToken
}

function errorMessage(body: unknown) {
  if (!body || typeof body !== "object") return "We could not complete that request."
  const values = Object.values(body as Record<string, unknown>)
  for (const value of values) {
    if (typeof value === "string") return value
    if (Array.isArray(value) && typeof value[0] === "string") return value[0]
    if (value && typeof value === "object") {
      const nested = Object.values(value as Record<string, unknown>)[0]
      if (typeof nested === "string") return nested
      if (Array.isArray(nested) && typeof nested[0] === "string") return nested[0]
    }
  }
  return "We could not complete that request."
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase()
  const headers = new Headers(options.headers)
  headers.set("Accept", "application/json")
  if (options.body) headers.set("Content-Type", "application/json")
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    headers.set("X-CSRFToken", await ensureCsrfToken())
  }
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  })
  if (response.status === 204) return undefined as T
  const body = await response.json().catch(() => null)
  if (!response.ok) throw new ReaderApiError(response.status, errorMessage(body))
  return body as T
}

export async function currentReader() {
  try {
    return await request<ArchiveReader>("/auth/me/")
  } catch (error) {
    if (error instanceof ReaderApiError && [401, 403].includes(error.status)) return null
    throw error
  }
}

export async function signInReader(email: string, password: string) {
  const reader = await request<ArchiveReader>("/auth/sign-in/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  })
  await ensureCsrfToken(true)
  return reader
}

export async function registerReader(payload: ReaderRegistration) {
  const reader = await request<ArchiveReader>("/auth/register/", {
    method: "POST",
    body: JSON.stringify(payload),
  })
  await ensureCsrfToken(true)
  return reader
}

export async function signOutReader() {
  await request<void>("/auth/sign-out/", { method: "POST" })
  csrfToken = null
}

export const getPostEngagement = (slug: string) =>
  request<PostEngagement>(`/archives/posts/${encodeURIComponent(slug)}/engagement/`)

export const likePost = (slug: string) =>
  request<Pick<PostEngagement, "liked" | "like_count">>(
    `/archives/posts/${encodeURIComponent(slug)}/like/`,
    { method: "PUT" },
  )

export const unlikePost = (slug: string) =>
  request<Pick<PostEngagement, "liked" | "like_count">>(
    `/archives/posts/${encodeURIComponent(slug)}/like/`,
    { method: "DELETE" },
  )

export const addPostComment = (slug: string, body: string) =>
  request<ArchiveComment>(
    `/archives/posts/${encodeURIComponent(slug)}/comments/`,
    { method: "POST", body: JSON.stringify({ body }) },
  )

export const getSubscription = () =>
  request<SubscriptionState>("/archives/subscription/")

export const subscribe = () =>
  request<SubscriptionState>("/archives/subscription/", { method: "PUT" })

export const unsubscribe = () =>
  request<SubscriptionState>("/archives/subscription/", { method: "DELETE" })

export const getNotifications = () =>
  request<NotificationState>("/archives/notifications/")

export const markNotificationsRead = () =>
  request<Pick<NotificationState, "unread_count" | "results">>(
    "/archives/notifications/read/",
    { method: "POST" },
  )
