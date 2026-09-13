import { computed, ref } from "vue"
import { defineStore } from "pinia"
import {
  currentReader,
  getNotifications,
  getSubscription,
  markNotificationsRead,
  ReaderApiError,
  registerReader,
  signInReader,
  signOutReader,
  subscribe,
  unsubscribe,
  type ArchiveReader,
  type NotificationState,
  type ReaderRegistration,
} from "./readerApi"

export const useArchiveReaderStore = defineStore("archive-reader", () => {
  const user = ref<ArchiveReader | null>(null)
  const state = ref<"idle" | "loading" | "authenticated" | "anonymous">("idle")
  const subscribed = ref(false)
  const notifications = ref<NotificationState>({
    subscribed: false,
    unread_count: 0,
    results: [],
  })
  const error = ref("")
  const busy = ref(false)
  let initialization: Promise<void> | null = null

  const isAuthenticated = computed(() => state.value === "authenticated" && Boolean(user.value))
  const displayName = computed(() => user.value?.first_name || user.value?.email || "Reader")

  function setError(value: unknown) {
    error.value = value instanceof ReaderApiError ? value.message : "Something went wrong. Please try again."
  }

  async function refreshReaderState() {
    if (!user.value) return
    const [subscription, notificationState] = await Promise.all([
      getSubscription(),
      getNotifications(),
    ])
    subscribed.value = subscription.subscribed
    notifications.value = notificationState
  }

  async function initialize(force = false) {
    if (!force && state.value !== "idle") return initialization || undefined
    if (initialization) return initialization
    state.value = "loading"
    initialization = (async () => {
      try {
        user.value = await currentReader()
        state.value = user.value ? "authenticated" : "anonymous"
        if (user.value) await refreshReaderState()
      } catch (requestError) {
        state.value = "anonymous"
        setError(requestError)
      } finally {
        initialization = null
      }
    })()
    return initialization
  }

  async function authenticate(action: () => Promise<ArchiveReader>) {
    busy.value = true
    error.value = ""
    try {
      user.value = await action()
      state.value = "authenticated"
      await refreshReaderState()
    } catch (requestError) {
      setError(requestError)
      throw requestError
    } finally {
      busy.value = false
    }
  }

  const signIn = (email: string, password: string) =>
    authenticate(() => signInReader(email, password))

  const register = (payload: ReaderRegistration) =>
    authenticate(() => registerReader(payload))

  async function signOut() {
    busy.value = true
    error.value = ""
    try {
      await signOutReader()
      user.value = null
      state.value = "anonymous"
      subscribed.value = false
      notifications.value = { subscribed: false, unread_count: 0, results: [] }
    } catch (requestError) {
      setError(requestError)
      throw requestError
    } finally {
      busy.value = false
    }
  }

  async function toggleSubscription() {
    busy.value = true
    error.value = ""
    try {
      const result = subscribed.value ? await unsubscribe() : await subscribe()
      subscribed.value = result.subscribed
      notifications.value = await getNotifications()
    } catch (requestError) {
      setError(requestError)
      throw requestError
    } finally {
      busy.value = false
    }
  }

  async function markAllRead() {
    busy.value = true
    error.value = ""
    try {
      const result = await markNotificationsRead()
      notifications.value = {
        ...notifications.value,
        unread_count: result.unread_count,
        results: result.results,
      }
    } catch (requestError) {
      setError(requestError)
      throw requestError
    } finally {
      busy.value = false
    }
  }

  return {
    user,
    state,
    subscribed,
    notifications,
    error,
    busy,
    isAuthenticated,
    displayName,
    initialize,
    refreshReaderState,
    signIn,
    register,
    signOut,
    toggleSubscription,
    markAllRead,
  }
})
