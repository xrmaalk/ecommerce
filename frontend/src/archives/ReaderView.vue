<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRoute } from "vue-router"
import { formatDate } from "./api"
import { useArchiveReaderStore } from "./readerStore"

const route = useRoute()
const reader = useArchiveReaderStore()
const mode = ref<"sign-in" | "register">("sign-in")
const signInForm = reactive({ email: "", password: "" })
const registrationForm = reactive({
  first_name: "",
  last_name: "",
  email: "",
  password: "",
  password_confirm: "",
})
const returnTo = computed(() => {
  const value = route.query.returnTo
  return typeof value === "string" && value.startsWith("/") && !value.startsWith("//")
    ? value
    : "/"
})

onMounted(() => reader.initialize())

async function submitSignIn() {
  try {
    await reader.signIn(signInForm.email, signInForm.password)
    signInForm.password = ""
  } catch {
    // The store exposes a safe error message in the view.
  }
}

async function submitRegistration() {
  try {
    await reader.register({ ...registrationForm })
    registrationForm.password = ""
    registrationForm.password_confirm = ""
  } catch {
    // The store exposes a safe error message in the view.
  }
}

async function toggleSubscription() {
  try {
    await reader.toggleSubscription()
  } catch {
    // The store exposes a safe error message in the view.
  }
}

async function markAllRead() {
  try {
    await reader.markAllRead()
  } catch {
    // The store exposes a safe error message in the view.
  }
}

async function signOut() {
  try {
    await reader.signOut()
  } catch {
    // The store exposes a safe error message in the view.
  }
}
</script>

<template>
  <section class="reader-account">
    <header class="reader-account__intro">
      <p class="eyebrow">READER ACCESS</p>
      <h1>Your place in the archives.</h1>
      <p>
        Subscribe for new-post notifications, save a little appreciation with a
        like, and join the conversation. Reader accounts never have publishing
        access.
      </p>
    </header>

    <div v-if="reader.state === 'loading'" class="feed-state" role="status">
      <h2>Opening your reader account…</h2>
    </div>

    <div v-else-if="!reader.isAuthenticated" class="reader-auth-card">
      <div class="reader-auth-tabs" role="tablist" aria-label="Reader account">
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'sign-in'"
          :class="{ selected: mode === 'sign-in' }"
          @click="mode = 'sign-in'">
          Sign in
        </button>
        <button
          type="button"
          role="tab"
          :aria-selected="mode === 'register'"
          :class="{ selected: mode === 'register' }"
          @click="mode = 'register'">
          Create account
        </button>
      </div>

      <form v-if="mode === 'sign-in'" @submit.prevent="submitSignIn">
        <label for="reader-email">Email address</label>
        <input
          id="reader-email"
          v-model.trim="signInForm.email"
          type="email"
          autocomplete="email"
          required />
        <label for="reader-password">Password</label>
        <input
          id="reader-password"
          v-model="signInForm.password"
          type="password"
          autocomplete="current-password"
          required />
        <button class="solid-button" type="submit" :disabled="reader.busy">
          {{ reader.busy ? "Signing in…" : "Sign in as a reader" }}
        </button>
      </form>

      <form v-else @submit.prevent="submitRegistration">
        <div class="reader-form-row">
          <div>
            <label for="reader-first-name">First name</label>
            <input
              id="reader-first-name"
              v-model.trim="registrationForm.first_name"
              autocomplete="given-name"
              maxlength="150"
              required />
          </div>
          <div>
            <label for="reader-last-name">Last name</label>
            <input
              id="reader-last-name"
              v-model.trim="registrationForm.last_name"
              autocomplete="family-name"
              maxlength="150"
              required />
          </div>
        </div>
        <label for="register-reader-email">Email address</label>
        <input
          id="register-reader-email"
          v-model.trim="registrationForm.email"
          type="email"
          autocomplete="email"
          required />
        <label for="register-reader-password">Password</label>
        <input
          id="register-reader-password"
          v-model="registrationForm.password"
          type="password"
          autocomplete="new-password"
          required />
        <label for="register-reader-confirm">Confirm password</label>
        <input
          id="register-reader-confirm"
          v-model="registrationForm.password_confirm"
          type="password"
          autocomplete="new-password"
          required />
        <button class="solid-button" type="submit" :disabled="reader.busy">
          {{ reader.busy ? "Creating account…" : "Create reader account" }}
        </button>
      </form>
      <p v-if="reader.error" class="reader-feedback reader-feedback--error" role="alert">
        {{ reader.error }}
      </p>
    </div>

    <div v-else class="reader-dashboard">
      <section class="reader-profile-card">
        <div>
          <span class="eyebrow">SIGNED IN</span>
          <h2>{{ reader.displayName }}</h2>
          <p>{{ reader.user?.email }}</p>
        </div>
        <div class="reader-profile-actions">
          <RouterLink class="text-link" :to="returnTo">Return to reading →</RouterLink>
          <button type="button" class="quiet-button" :disabled="reader.busy" @click="signOut">
            Sign out
          </button>
        </div>
      </section>

      <section class="subscription-card">
        <div>
          <span class="eyebrow">NEW POST NOTIFICATIONS</span>
          <h2>{{ reader.subscribed ? "You’re subscribed." : "Stay close to the journal." }}</h2>
          <p>
            {{
              reader.subscribed
                ? "Newly published stories will appear here."
                : "Subscribe to see new articles, releases, and updates in your reader account."
            }}
          </p>
        </div>
        <button
          type="button"
          :class="reader.subscribed ? 'quiet-button' : 'solid-button'"
          :disabled="reader.busy"
          @click="toggleSubscription">
          {{ reader.subscribed ? "Unsubscribe" : "Subscribe" }}
        </button>
      </section>

      <section v-if="reader.subscribed" class="notification-card">
        <header>
          <div>
            <span class="eyebrow">YOUR NOTIFICATIONS</span>
            <h2>
              {{ reader.notifications.unread_count }}
              {{ reader.notifications.unread_count === 1 ? "new post" : "new posts" }}
            </h2>
          </div>
          <button
            v-if="reader.notifications.unread_count"
            type="button"
            class="quiet-button"
            :disabled="reader.busy"
            @click="markAllRead">
            Mark all read
          </button>
        </header>
        <ol v-if="reader.notifications.results.length" class="notification-list">
          <li v-for="post in reader.notifications.results" :key="post.id">
            <RouterLink :to="{ name: 'post', params: { slug: post.slug } }">
              <span>{{ post.title }}</span>
              <time :datetime="post.published_at">{{ formatDate(post.published_at) }}</time>
            </RouterLink>
          </li>
        </ol>
        <p v-else class="empty-notifications">You’re all caught up.</p>
      </section>
    </div>
  </section>
</template>
