<script setup lang="ts">
import { formatCad } from "../../composables/useCurrency"
import { useRouter } from "vue-router"
import { useAuthStore } from "../../stores/auth"
defineProps<{ subtotal: number; itemCount: number; compact?: boolean }>()
const auth = useAuthStore()
const router = useRouter()

function proceed() {
  if (auth.isAuthenticated) void router.push({ name: "checkout" })
  else void router.push({ name: "account", query: { redirect: "/checkout" } })
}
</script>

<template>
  <section class="bag-summary" :class="{ 'bag-summary--compact': compact }" aria-labelledby="bag-summary-title">
    <h2 id="bag-summary-title">Order summary</h2>
    <dl><div><dt>Items ({{ itemCount }})</dt><dd>{{ formatCad(subtotal) }}</dd></div><div><dt>Shipping</dt><dd>Calculated at checkout</dd></div></dl>
    <div class="bag-summary__total"><span>Subtotal</span><strong>{{ formatCad(subtotal) }} <small>CAD</small></strong></div>
    <p>Taxes and shipping are calculated at checkout.</p>
    <button type="button" class="button button--primary button--wide" aria-describedby="checkout-note" @click="proceed">Proceed to checkout</button>
    <small id="checkout-note" class="checkout-note">Secure PayPal checkout. Sign-in is required.</small>
  </section>
</template>
