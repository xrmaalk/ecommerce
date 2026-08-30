import axios from "axios"
import { computed, ref } from "vue"
import { defineStore } from "pinia"
import { api, ensureCsrfToken, getApiErrorMessage } from "../api/client"
import type {
  Customer,
  PasswordPayload,
  ProfilePayload,
  RegistrationPayload,
  SignInPayload,
} from "../types/auth"

export type AuthState = "idle" | "loading" | "authenticated" | "anonymous"

export const useAuthStore = defineStore("auth", () => {
  const user = ref<Customer | null>(null)
  const state = ref<AuthState>("idle")
  const isSubmitting = ref(false)
  const error = ref("")
  const statusMessage = ref("")
  let initialization: Promise<void> | null = null

  const isAuthenticated = computed(() => state.value === "authenticated" && Boolean(user.value))
  const displayName = computed(() => user.value?.first_name || user.value?.email || "Account")

  async function initialize(force = false) {
    if (!force && (state.value === "authenticated" || state.value === "anonymous")) return
    if (initialization) return initialization

    state.value = "loading"
    initialization = (async () => {
      try {
        await ensureCsrfToken(force)
        const response = await api.get<Customer>("/auth/me/")
        user.value = response.data
        state.value = "authenticated"
      } catch (requestError) {
        if (axios.isAxiosError(requestError) && [401, 403].includes(requestError.response?.status ?? 0)) {
          user.value = null
          state.value = "anonymous"
        } else {
          state.value = "anonymous"
          error.value = getApiErrorMessage(requestError)
        }
      } finally {
        initialization = null
      }
    })()
    return initialization
  }

  async function runAuthRequest(request: () => Promise<Customer>, successMessage: string) {
    isSubmitting.value = true
    error.value = ""
    statusMessage.value = ""
    try {
      const customer = await request()
      user.value = customer
      state.value = "authenticated"
      await ensureCsrfToken(true)
      statusMessage.value = successMessage
    } catch (requestError) {
      error.value = getApiErrorMessage(requestError)
      throw requestError
    } finally {
      isSubmitting.value = false
    }
  }

  async function signIn(payload: SignInPayload) {
    await runAuthRequest(
      async () => (await api.post<Customer>("/auth/sign-in/", payload)).data,
      "Welcome back. You are signed in.",
    )
  }

  async function register(payload: RegistrationPayload) {
    await runAuthRequest(
      async () => (await api.post<Customer>("/auth/register/", payload)).data,
      "Your Organic Emperor account is ready.",
    )
  }

  async function signOut() {
    isSubmitting.value = true
    error.value = ""
    try {
      await api.post("/auth/sign-out/")
      user.value = null
      state.value = "anonymous"
      statusMessage.value = "You have been signed out safely."
      await ensureCsrfToken(true)
    } catch (requestError) {
      error.value = getApiErrorMessage(requestError)
      throw requestError
    } finally {
      isSubmitting.value = false
    }
  }

  async function updateProfile(payload: ProfilePayload) {
    isSubmitting.value = true
    error.value = ""
    statusMessage.value = ""
    try {
      user.value = (await api.patch<Customer>("/auth/me/", payload)).data
      statusMessage.value = "Your profile has been updated."
    } catch (requestError) {
      error.value = getApiErrorMessage(requestError)
      throw requestError
    } finally {
      isSubmitting.value = false
    }
  }

  async function changePassword(payload: PasswordPayload) {
    isSubmitting.value = true
    error.value = ""
    statusMessage.value = ""
    try {
      await api.post("/auth/password/", payload)
      await ensureCsrfToken(true)
      statusMessage.value = "Your password has been changed."
    } catch (requestError) {
      error.value = getApiErrorMessage(requestError)
      throw requestError
    } finally {
      isSubmitting.value = false
    }
  }

  function clearFeedback() {
    error.value = ""
    statusMessage.value = ""
  }

  return {
    user, state, isSubmitting, error, statusMessage, isAuthenticated, displayName,
    initialize, signIn, register, signOut, updateProfile, changePassword, clearFeedback,
  }
})
