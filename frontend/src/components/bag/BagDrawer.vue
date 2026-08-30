<script setup lang="ts">
import { nextTick, onBeforeUnmount, ref, watch } from "vue"
import { useBagStore } from "../../stores/bag"
import BagLineItem from "./BagLineItem.vue"
import EmptyBag from "./EmptyBag.vue"
import { formatCad } from "../../composables/useCurrency"

const bag = useBagStore()
const dialog = ref<HTMLElement | null>(null)
let previouslyFocused: HTMLElement | null = null

function close() { bag.close() }
function handleKeydown(event: KeyboardEvent) {
  if (event.key === "Escape") close()
  if (event.key !== "Tab" || !dialog.value) return
  const controls = [...dialog.value.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled])')]
  if (!controls.length) return
  const first = controls[0]
  const last = controls[controls.length - 1]
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
}

watch(() => bag.isOpen, async (isOpen) => {
  document.body.classList.toggle("drawer-open", isOpen)
  if (isOpen) {
    previouslyFocused = document.activeElement as HTMLElement | null
    await nextTick()
    dialog.value?.querySelector<HTMLElement>("button")?.focus()
  } else previouslyFocused?.focus()
})

onBeforeUnmount(() => document.body.classList.remove("drawer-open"))
</script>

<template>
  <Teleport to="body">
    <Transition name="bag">
      <div v-if="bag.isOpen" class="bag-layer" @keydown="handleKeydown">
        <button type="button" class="bag-backdrop" aria-label="Close shopping bag" @click="close"></button>
        <aside ref="dialog" class="bag-drawer" role="dialog" aria-modal="true" aria-labelledby="bag-drawer-title">
          <header><div><small>Your selections</small><h2 id="bag-drawer-title">Shopping bag</h2></div><button type="button" class="close-button" aria-label="Close shopping bag" @click="close">×</button></header>
          <div v-if="!bag.isEmpty" class="bag-drawer__items">
            <BagLineItem v-for="item in bag.items" :key="item.id" :item="item" compact
              @increase="bag.increment(item.id)" @decrease="bag.decrement(item.id)" @remove="bag.remove(item.id)" />
          </div>
          <EmptyBag v-else drawer @continue="close" />
          <footer v-if="!bag.isEmpty">
            <div><span>Subtotal</span><strong>{{ formatCad(bag.subtotal) }}</strong></div>
            <p>Taxes and shipping calculated at checkout.</p>
            <RouterLink class="button button--primary button--wide" to="/bag" @click="close">View full bag</RouterLink>
          </footer>
        </aside>
      </div>
    </Transition>
  </Teleport>
</template>
