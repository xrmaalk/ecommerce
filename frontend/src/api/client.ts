import axios, { AxiosError } from "axios"

const baseURL = import.meta.env.VITE_API_BASE_URL

if (!baseURL) {
  throw new Error(
    "VITE_API_BASE_URL is missing. Check the active Vite environment file.",
  )
}

export const api = axios.create({
  baseURL: baseURL.replace(/\/+$/, ""),
  timeout: 10_000,
  withCredentials: true,
  headers: { Accept: "application/json" },
})

let csrfToken: string | null = null
let csrfRequest: Promise<string> | null = null

export async function ensureCsrfToken(force = false): Promise<string> {
  if (csrfToken && !force) return csrfToken
  if (csrfRequest) return csrfRequest

  csrfRequest = api.get<{ csrf_token: string }>("/auth/csrf/")
    .then(({ data }) => {
      csrfToken = data.csrf_token
      return csrfToken
    })
    .finally(() => { csrfRequest = null })

  return csrfRequest
}

api.interceptors.request.use(async (config) => {
  const method = config.method?.toLowerCase() ?? "get"
  if (!["get", "head", "options"].includes(method)) {
    config.headers.set("X-CSRFToken", await ensureCsrfToken())
  }
  return config
})

type ApiErrorBody = {
  detail?: string
  [field: string]: string | string[] | undefined
}

export function getApiErrorMessage(error: unknown): string {
  if (!(error instanceof AxiosError)) return "Something went wrong. Please try again."
  if (!error.response) return "We could not reach the store. Check your connection and try again."

  const body = error.response.data as ApiErrorBody | undefined
  if (typeof body?.detail === "string") return body.detail
  if (body) {
    for (const value of Object.values(body)) {
      if (typeof value === "string") return value
      if (Array.isArray(value) && typeof value[0] === "string") return value[0]
    }
  }
  return "We could not complete that request. Please review the form and try again."
}
