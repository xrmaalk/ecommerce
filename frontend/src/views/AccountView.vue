<script setup lang="ts">
import { computed, reactive, ref, watch } from "vue"
import { storeToRefs } from "pinia"
import { useRoute, useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const { user, state, isSubmitting, error, statusMessage, isAuthenticated } = storeToRefs(auth)
const activeForm = ref<"sign-in" | "register" | "profile" | "password" | "">("")

const signInForm = reactive({ email: "", password: "" })
const registrationForm = reactive({
  first_name: "", last_name: "", email: "", password: "", password_confirm: "",
})
const profileForm = reactive({ first_name: "", last_name: "", email: "" })
const passwordForm = reactive({
  current_password: "", new_password: "", new_password_confirm: "",
})

const memberSince = computed(() => user.value
  ? new Intl.DateTimeFormat("en-CA", { month: "long", year: "numeric" }).format(new Date(user.value.date_joined))
  : "")

watch(user, (customer) => {
  if (!customer) return
  profileForm.first_name = customer.first_name
  profileForm.last_name = customer.last_name
  profileForm.email = customer.email
}, { immediate: true })

function begin(form: typeof activeForm.value) {
  activeForm.value = form
  auth.clearFeedback()
}

async function finishAuthentication(action: () => Promise<void>) {
  try {
    await action()
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/account/settings"
    await router.replace(redirect)
  } catch { /* The store exposes a safe, user-facing error. */ }
}

async function submitSignIn() {
  begin("sign-in")
  await finishAuthentication(() => auth.signIn({ ...signInForm }))
}

async function submitRegistration() {
  begin("register")
  await finishAuthentication(() => auth.register({ ...registrationForm }))
}

async function submitProfile() {
  begin("profile")
  try { await auth.updateProfile({ ...profileForm }) } catch { /* Displayed below. */ }
}

async function submitPassword() {
  begin("password")
  try {
    await auth.changePassword({ ...passwordForm })
    passwordForm.current_password = ""
    passwordForm.new_password = ""
    passwordForm.new_password_confirm = ""
  } catch { /* Displayed below. */ }
}

async function submitSignOut() {
  begin("")
  try {
    await auth.signOut()
    await router.replace({ name: "account" })
  } catch { /* Displayed below. */ }
}
</script>

<template>
  <section class="page-shell account-page">
    <header class="account-heading">
      <div>
        <p class="eyebrow">Organic Emperor</p>
        <h1>{{ isAuthenticated ? `Welcome, ${user?.first_name}` : "Your account" }}</h1>
        <p>{{ isAuthenticated ? "Manage your details and account security." : "Sign in for a smoother, more personal shopping experience." }}</p>
      </div>
      <div v-if="isAuthenticated" class="account-heading__mark" aria-hidden="true">OE</div>
    </header>

    <div v-if="state === 'loading'" class="account-loading" role="status">
      <span class="account-spinner" aria-hidden="true"></span>
      Checking your account…
    </div>

    <template v-else-if="!isAuthenticated">
      <div v-if="statusMessage" class="form-alert form-alert--success" role="status">{{ statusMessage }}</div>
      <div class="auth-grid">
        <form class="account-card" @submit.prevent="submitSignIn">
          <div class="account-card__heading">
            <p class="eyebrow">Welcome back</p>
            <h2>Sign in</h2>
            <p>Access your account securely from this device.</p>
          </div>
          <div class="form-field">
            <label for="sign-in-email">Email address</label>
            <input id="sign-in-email" v-model.trim="signInForm.email" type="email" autocomplete="email"
              maxlength="254" required placeholder="you@example.com" />
          </div>
          <div class="form-field">
            <label for="sign-in-password">Password</label>
            <input id="sign-in-password" v-model="signInForm.password" type="password" autocomplete="current-password"
              required placeholder="Your password" />
          </div>
          <div v-if="activeForm === 'sign-in' && error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
          <button class="button button--primary button--wide" type="submit" :disabled="isSubmitting">
            {{ isSubmitting && activeForm === "sign-in" ? "Signing in…" : "Sign in" }}
          </button>
        </form>

        <form class="account-card account-card--accent" @submit.prevent="submitRegistration">
          <div class="account-card__heading">
            <p class="eyebrow">New here?</p>
            <h2>Create an account</h2>
            <p>Save your details now and be ready for order history and checkout.</p>
          </div>
          <div class="form-row">
            <div class="form-field">
              <label for="first-name">First name</label>
              <input id="first-name" v-model.trim="registrationForm.first_name" autocomplete="given-name"
                maxlength="150" required />
            </div>
            <div class="form-field">
              <label for="last-name">Last name</label>
              <input id="last-name" v-model.trim="registrationForm.last_name" autocomplete="family-name"
                maxlength="150" required />
            </div>
          </div>
          <div class="form-field">
            <label for="register-email">Email address</label>
            <input id="register-email" v-model.trim="registrationForm.email" type="email" autocomplete="email"
              maxlength="254" required placeholder="you@example.com" />
          </div>
          <div class="form-row">
            <div class="form-field">
              <label for="register-password">Password</label>
              <input id="register-password" v-model="registrationForm.password" type="password" autocomplete="new-password"
                minlength="8" required />
            </div>
            <div class="form-field">
              <label for="register-password-confirm">Confirm password</label>
              <input id="register-password-confirm" v-model="registrationForm.password_confirm" type="password"
                autocomplete="new-password" minlength="8" required />
            </div>
          </div>
          <p class="form-help">Use at least 8 characters and avoid common or entirely numeric passwords.</p>
          <div v-if="activeForm === 'register' && error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
          <button class="button button--primary button--wide" type="submit" :disabled="isSubmitting">
            {{ isSubmitting && activeForm === "register" ? "Creating account…" : "Create account" }}
          </button>
          <p class="account-consent">By creating an account, you acknowledge our <RouterLink :to="{ name: 'privacy' }">Privacy Policy</RouterLink>.</p>
        </form>
      </div>
      <aside class="security-note">
        <strong>Protected by design</strong>
        <span>Your password stays with Organic Emperor’s secure server and is never stored in your browser.</span>
      </aside>
    </template>

    <template v-else>
      <div v-if="statusMessage" class="form-alert form-alert--success" role="status">{{ statusMessage }}</div>
      <div v-if="error && activeForm === ''" class="form-alert form-alert--error" role="alert">{{ error }}</div>
      <div class="account-dashboard">
        <aside class="account-summary">
          <div class="account-avatar" aria-hidden="true">{{ user?.first_name?.charAt(0) }}{{ user?.last_name?.charAt(0) }}</div>
          <h2>{{ user?.first_name }} {{ user?.last_name }}</h2>
          <p>{{ user?.email }}</p>
          <small>Member since {{ memberSince }}</small>
          <RouterLink class="button button--primary button--wide" :to="{ name: 'home', hash: '#catalog' }">Continue shopping</RouterLink>
          <RouterLink class="button account-summary__orders button--wide" :to="{ name: 'orders' }">Order history</RouterLink>
          <button class="text-button" type="button" :disabled="isSubmitting" @click="submitSignOut">Sign out</button>
        </aside>

        <div class="account-settings">
          <form class="account-card" @submit.prevent="submitProfile">
            <div class="account-card__heading">
              <p class="eyebrow">Profile</p>
              <h2>Your details</h2>
              <p>Keep your contact information current for future orders.</p>
            </div>
            <div class="form-row">
              <div class="form-field">
                <label for="profile-first-name">First name</label>
                <input id="profile-first-name" v-model.trim="profileForm.first_name" autocomplete="given-name" maxlength="150" required />
              </div>
              <div class="form-field">
                <label for="profile-last-name">Last name</label>
                <input id="profile-last-name" v-model.trim="profileForm.last_name" autocomplete="family-name" maxlength="150" required />
              </div>
            </div>
            <div class="form-field">
              <label for="profile-email">Email address</label>
              <input id="profile-email" v-model.trim="profileForm.email" type="email" autocomplete="email" maxlength="254" required />
            </div>
            <div v-if="activeForm === 'profile' && error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
            <button class="button button--primary" type="submit" :disabled="isSubmitting">
              {{ isSubmitting && activeForm === "profile" ? "Saving…" : "Save details" }}
            </button>
          </form>

          <form class="account-card" @submit.prevent="submitPassword">
            <div class="account-card__heading">
              <p class="eyebrow">Security</p>
              <h2>Change password</h2>
              <p>Your session stays active after a successful password change.</p>
            </div>
            <div class="form-field">
              <label for="current-password">Current password</label>
              <input id="current-password" v-model="passwordForm.current_password" type="password" autocomplete="current-password" required />
            </div>
            <div class="form-row">
              <div class="form-field">
                <label for="new-password">New password</label>
                <input id="new-password" v-model="passwordForm.new_password" type="password" autocomplete="new-password" minlength="8" required />
              </div>
              <div class="form-field">
                <label for="new-password-confirm">Confirm new password</label>
                <input id="new-password-confirm" v-model="passwordForm.new_password_confirm" type="password" autocomplete="new-password" minlength="8" required />
              </div>
            </div>
            <div v-if="activeForm === 'password' && error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
            <button class="button button--primary" type="submit" :disabled="isSubmitting">
              {{ isSubmitting && activeForm === "password" ? "Updating…" : "Update password" }}
            </button>
          </form>
        </div>
      </div>
    </template>
  </section>
</template>
