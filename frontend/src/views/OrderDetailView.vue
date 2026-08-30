<script setup lang="ts">
import { onMounted, ref } from "vue"
import { useRoute } from "vue-router"
import { api, getApiErrorMessage } from "../api/client"
import { formatCad } from "../composables/useCurrency"
import type { Order } from "../types/commerce"

const route = useRoute()
const order = ref<Order | null>(null)
const error = ref("")
onMounted(async () => {
  try { order.value = (await api.get<Order>(`/commerce/orders/${String(route.params.number)}/`)).data }
  catch (requestError) { error.value = getApiErrorMessage(requestError) }
})
</script>

<template>
  <section class="page-shell order-detail-page">
    <div v-if="error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
    <div v-else-if="!order" class="account-loading" role="status">Loading order…</div>
    <template v-else>
      <header class="page-heading"><p class="eyebrow">Payment received</p><h1>Thank you</h1><p>Order {{ order.number }} is confirmed and safely recorded.</p></header>
      <div class="order-detail-grid">
        <section class="account-card"><h2>Items</h2><div v-for="item in order.items" :key="item.sku" class="order-line"><div><strong>{{ item.name }}</strong><small>{{ item.sku }} · Qty {{ item.quantity }}</small></div><span>{{ formatCad(Number(item.line_total_cad)) }}</span></div></section>
        <aside class="bag-summary"><h2>Summary</h2><dl><div><dt>Subtotal</dt><dd>{{ formatCad(Number(order.subtotal_cad)) }}</dd></div><div><dt>Shipping</dt><dd>{{ formatCad(Number(order.shipping_cad)) }}</dd></div><div><dt>Tax</dt><dd>{{ formatCad(Number(order.tax_cad)) }}</dd></div></dl><div class="bag-summary__total"><span>Total</span><strong>{{ formatCad(Number(order.total_cad)) }} <small>CAD</small></strong></div><RouterLink class="button button--primary button--wide" :to="{ name: 'orders' }">View all orders</RouterLink></aside>
      </div>
    </template>
  </section>
</template>

