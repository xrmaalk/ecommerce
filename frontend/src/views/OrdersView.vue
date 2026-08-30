<script setup lang="ts">
import { onMounted, ref } from "vue"
import { api, getApiErrorMessage } from "../api/client"
import { formatCad } from "../composables/useCurrency"
import type { Order } from "../types/commerce"

const orders = ref<Order[]>([])
const loading = ref(true)
const error = ref("")
onMounted(async () => {
  try {
    const response = await api.get<{ results?: Order[] } | Order[]>("/commerce/orders/")
    orders.value = Array.isArray(response.data) ? response.data : response.data.results ?? []
  } catch (requestError) { error.value = getApiErrorMessage(requestError) }
  finally { loading.value = false }
})
</script>

<template>
  <section class="page-shell orders-page">
    <header class="page-heading"><p class="eyebrow">Your account</p><h1>Order history</h1><p>Review paid orders and delivery details.</p></header>
    <div v-if="loading" class="account-loading" role="status">Loading orders…</div>
    <div v-else-if="error" class="form-alert form-alert--error" role="alert">{{ error }}</div>
    <div v-else-if="!orders.length" class="notice-card"><h2>No orders yet</h2><p>Your completed PayPal orders will appear here.</p><RouterLink class="button button--primary" :to="{ name: 'home', hash: '#catalog' }">Start shopping</RouterLink></div>
    <div v-else class="order-list">
      <RouterLink v-for="order in orders" :key="order.id" class="order-card" :to="{ name: 'order-detail', params: { number: order.number } }">
        <div><small>Order</small><strong>{{ order.number }}</strong></div>
        <div><small>Paid</small><span>{{ new Date(order.paid_at).toLocaleDateString('en-CA') }}</span></div>
        <div><small>Status</small><span class="order-status">{{ order.status }}</span></div>
        <div><small>Total</small><strong>{{ formatCad(Number(order.total_cad)) }}</strong></div>
      </RouterLink>
    </div>
  </section>
</template>

