<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"
import { api, getApiErrorMessage } from "../api/client"
import PayPalButtons from "../components/checkout/PayPalButtons.vue"
import { formatCad } from "../composables/useCurrency"
import { useAuthStore } from "../stores/auth"
import { useBagStore } from "../stores/bag"
import type { CheckoutConfig, CheckoutSession, Order, ShippingAddress, ShippingRate } from "../types/commerce"

const auth = useAuthStore()
const bag = useBagStore()
const router = useRouter()
const rates = ref<ShippingRate[]>([])
const config = ref<CheckoutConfig | null>(null)
const quote = ref<CheckoutSession | null>(null)
const error = ref("")
const isQuoting = ref(false)

const address = reactive<ShippingAddress>({
  first_name: auth.user?.first_name ?? "",
  last_name: auth.user?.last_name ?? "",
  address_line_1: "", address_line_2: "", city: "", region: "", postal_code: "",
  country_code: "CA", phone: "",
})

const selectedRate = computed(() => rates.value.find((rate) => rate.country_code === address.country_code))

onMounted(async () => {
  try {
    const [ratesResponse, configResponse] = await Promise.all([
      api.get<ShippingRate[]>("/commerce/shipping-rates/"),
      api.get<CheckoutConfig>("/commerce/checkout/config/"),
    ])
    rates.value = ratesResponse.data
    config.value = configResponse.data
  } catch (requestError) { error.value = getApiErrorMessage(requestError) }
})

async function requestQuote() {
  isQuoting.value = true
  error.value = ""
  quote.value = null
  try {
    quote.value = (await api.post<CheckoutSession>("/commerce/checkout/quote/", address)).data
  } catch (requestError) { error.value = getApiErrorMessage(requestError) }
  finally { isQuoting.value = false }
}

function handleCompleted(order: Order) {
  bag.clearAfterOrder()
  void router.replace({ name: "order-detail", params: { number: order.number } })
}
</script>

<template>
  <section class="page-shell checkout-page">
    <header class="page-heading">
      <p class="eyebrow">Secure checkout</p>
      <h1>Delivery & payment</h1>
      <p>Confirm your delivery address, review the server-calculated total, then complete payment with PayPal.</p>
    </header>

    <div v-if="bag.isEmpty" class="notice-card">
      <h2>Your bag is empty</h2>
      <p>Add something to your bag before beginning checkout.</p>
      <RouterLink class="button button--primary" :to="{ name: 'home', hash: '#catalog' }">Browse products</RouterLink>
    </div>

    <div v-else class="checkout-layout">
      <form class="checkout-form account-card" @submit.prevent="requestQuote">
        <div class="account-card__heading">
          <p class="eyebrow">Step one</p><h2>Shipping address</h2>
          <p>We currently ship to Canada and the United States using flat rates.</p>
        </div>
        <div class="form-row">
          <div class="form-field"><label for="checkout-first">First name</label><input id="checkout-first" v-model.trim="address.first_name" autocomplete="given-name" required /></div>
          <div class="form-field"><label for="checkout-last">Last name</label><input id="checkout-last" v-model.trim="address.last_name" autocomplete="family-name" required /></div>
        </div>
        <div class="form-field"><label for="checkout-address-one">Street address</label><input id="checkout-address-one" v-model.trim="address.address_line_1" autocomplete="address-line1" required /></div>
        <div class="form-field"><label for="checkout-address-two">Apartment, suite, etc. <span>(optional)</span></label><input id="checkout-address-two" v-model.trim="address.address_line_2" autocomplete="address-line2" /></div>
        <div class="form-row">
          <div class="form-field"><label for="checkout-city">City</label><input id="checkout-city" v-model.trim="address.city" autocomplete="address-level2" required /></div>
          <div class="form-field"><label for="checkout-region">Province or state</label><input id="checkout-region" v-model.trim="address.region" autocomplete="address-level1" required /></div>
        </div>
        <div class="form-row">
          <div class="form-field"><label for="checkout-postal">Postal or ZIP code</label><input id="checkout-postal" v-model.trim="address.postal_code" autocomplete="postal-code" required /></div>
          <div class="form-field"><label for="checkout-country">Country</label><select id="checkout-country" v-model="address.country_code" autocomplete="country" required><option value="CA">Canada</option><option value="US">United States</option></select></div>
        </div>
        <div class="form-field"><label for="checkout-phone">Phone <span>(optional)</span></label><input id="checkout-phone" v-model.trim="address.phone" type="tel" autocomplete="tel" /></div>
        <div v-if="selectedRate" class="shipping-rate"><span>{{ selectedRate.name }}</span><strong>{{ formatCad(Number(selectedRate.amount_cad)) }}</strong><small>{{ selectedRate.estimated_days_min }}–{{ selectedRate.estimated_days_max }} business days</small></div>
        <button class="button button--primary button--wide" type="submit" :disabled="isQuoting || !selectedRate">
          {{ isQuoting ? "Calculating securely…" : "Review order total" }}
        </button>
      </form>

      <aside class="checkout-summary bag-summary">
        <h2>Order total</h2>
        <dl>
          <div><dt>Items ({{ bag.itemCount }})</dt><dd>{{ formatCad(quote ? Number(quote.subtotal_cad) : bag.subtotal) }}</dd></div>
          <div><dt>Shipping</dt><dd>{{ quote ? formatCad(Number(quote.shipping_cad)) : "Calculated after address" }}</dd></div>
          <div><dt>Tax</dt><dd>{{ quote ? formatCad(Number(quote.tax_cad)) : "Pending tax adapter" }}</dd></div>
        </dl>
        <div class="bag-summary__total"><span>Total</span><strong>{{ formatCad(quote ? Number(quote.total_cad) : bag.subtotal) }} <small>CAD</small></strong></div>
        <div v-if="error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
        <div v-if="quote && config?.paypal_enabled" class="payment-panel">
          <p class="eyebrow">Step two</p><h3>Pay securely</h3>
          <PayPalButtons :client-id="config.paypal_client_id" :checkout-session-id="quote.id" @completed="handleCompleted" @error="error = $event" />
        </div>
        <div v-else-if="quote && !config?.paypal_enabled" class="form-alert form-alert--error">PayPal credentials are not configured on the server.</div>
        <p class="checkout-safety">Prices, stock, shipping, and tax are recalculated by the server before PayPal payment begins.</p>
      </aside>
    </div>
  </section>
</template>

