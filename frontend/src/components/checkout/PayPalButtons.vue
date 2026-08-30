<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue"
import { api, getApiErrorMessage } from "../../api/client"
import type { Order } from "../../types/commerce"

type PayPalButtonsInstance = { render: (target: HTMLElement) => Promise<void>; close?: () => void }
type PayPalNamespace = {
  Buttons: (options: {
    style: Record<string, string>
    createOrder: () => Promise<string>
    onApprove: () => Promise<void>
    onCancel: () => void
    onError: (error: unknown) => void
  }) => PayPalButtonsInstance
}

declare global { interface Window { paypal?: PayPalNamespace } }

const props = defineProps<{ clientId: string; checkoutSessionId: string }>()
const emit = defineEmits<{ completed: [order: Order]; error: [message: string] }>()
const container = ref<HTMLElement | null>(null)
let buttons: PayPalButtonsInstance | null = null

function loadSdk() {
  if (window.paypal) return Promise.resolve()
  return new Promise<void>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>("script[data-organic-emperor-paypal]")
    if (existing) {
      existing.addEventListener("load", () => resolve(), { once: true })
      existing.addEventListener("error", () => reject(new Error("PayPal checkout could not load.")), { once: true })
      return
    }
    const script = document.createElement("script")
    const params = new URLSearchParams({ "client-id": props.clientId, currency: "CAD", intent: "capture" })
    script.src = `https://www.paypal.com/sdk/js?${params}`
    script.async = true
    script.dataset.organicEmperorPaypal = "true"
    script.addEventListener("load", () => resolve(), { once: true })
    script.addEventListener("error", () => reject(new Error("PayPal checkout could not load.")), { once: true })
    document.head.append(script)
  })
}

onMounted(async () => {
  try {
    await loadSdk()
    if (!window.paypal || !container.value) throw new Error("PayPal checkout is unavailable.")
    buttons = window.paypal.Buttons({
      style: { layout: "vertical", shape: "rect", color: "gold", label: "paypal" },
      createOrder: async () => {
        const response = await api.post<{ paypal_order_id: string }>("/commerce/checkout/paypal/create/", {
          checkout_session_id: props.checkoutSessionId,
        })
        return response.data.paypal_order_id
      },
      onApprove: async () => {
        const response = await api.post<Order>("/commerce/checkout/paypal/capture/", {
          checkout_session_id: props.checkoutSessionId,
        })
        emit("completed", response.data)
      },
      onCancel: () => emit("error", "PayPal checkout was cancelled. Your bag is unchanged."),
      onError: (error) => emit("error", getApiErrorMessage(error)),
    })
    await buttons.render(container.value)
  } catch (error) {
    emit("error", getApiErrorMessage(error))
  }
})

onBeforeUnmount(() => { buttons?.close?.() })
</script>

<template><div ref="container" class="paypal-buttons" aria-label="Pay with PayPal"></div></template>

