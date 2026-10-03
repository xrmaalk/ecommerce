<script setup lang="ts">
import { computed, nextTick, reactive, ref, watch } from "vue"
import { useRoute } from "vue-router"
import { useAuthStore } from "../stores/auth"
import { useBagStore } from "../stores/bag"
import { bagRequestItems, buildContactDraft, contactEmail, contactMailto, MAX_MAILTO_LENGTH, type ContactForm, type RequestedItem } from "../contact"

const route = useRoute()
const auth = useAuthStore()
const bag = useBagStore()
const includeBag = ref(route.query.bag === "1")
const form = reactive<ContactForm>({
  requestType: "items",
  name: [auth.user?.first_name, auth.user?.last_name].filter(Boolean).join(" "),
  email: auth.user?.email || "", organization: "", purchaseOrder: "",
  destination: "", country: "", details: "",
})
const formElement = ref<HTMLFormElement | null>(null)
const preview = ref<HTMLTextAreaElement | null>(null)
const previewDetails = ref<HTMLDetailsElement | null>(null)
const previewHeading = ref<HTMLElement | null>(null)
const prepared = ref(false)
const status = ref("")

function queryText(name: string, maxLength: number) {
  const value = route.query[name]
  return typeof value === "string" ? value.slice(0, maxLength).replace(/[\u0000-\u001f\u007f]/g, " ").trim() : ""
}
const productItem = computed<RequestedItem | null>(() => {
  const name = queryText("item", 200)
  const slug = queryText("product", 200)
  if (!name || !/^[A-Za-z0-9_-]+$/.test(slug)) return null
  return { name, slug, variation: queryText("option", 200), sku: queryText("sku", 100), quantity: 1 }
})
const requestedItems = computed(() => [
  ...(productItem.value ? [productItem.value] : []),
  ...(includeBag.value ? bagRequestItems(bag.items) : []),
])
const draft = computed(() => buildContactDraft(form, requestedItems.value))
const emailUrl = computed(() => contactMailto(contactEmail, draft.value.subject, draft.value.body))
const needsCopy = computed(() => emailUrl.value.length > MAX_MAILTO_LENGTH)
const shortEmailUrl = computed(() => contactMailto(contactEmail, draft.value.subject))
const directEmailUrl = computed(() => contactMailto(contactEmail, "OrganicEmperor - Customer enquiry"))

watch([form, requestedItems], () => {
  prepared.value = false
  status.value = ""
  // A bag selection can make request text optional. Clear the previous custom
  // error so native form validation does not block the next submit handler.
  formElement.value?.querySelector<HTMLTextAreaElement>("#contact-details")?.setCustomValidity("")
}, { deep: true })
watch(() => route.query.bag, (value) => { includeBag.value = value === "1" })

async function prepareEmail() {
  const nameInput = formElement.value?.querySelector<HTMLInputElement>("#contact-name")
  nameInput?.setCustomValidity(form.name.trim() ? "" : "Please enter your name.")
  const detailsInput = formElement.value?.querySelector<HTMLTextAreaElement>("#contact-details")
  detailsInput?.setCustomValidity(requestedItems.value.length || form.details.trim() ? "" : "Please describe your request.")
  if (!formElement.value?.reportValidity() || !contactEmail) return
  prepared.value = true
  status.value = ""
  await nextTick()
  previewHeading.value?.focus()
}
async function copyRequest() {
  try {
    await navigator.clipboard.writeText(draft.value.body)
    status.value = "Request copied. Paste it into your email before sending."
  } catch {
    if (previewDetails.value) previewDetails.value.open = true
    await nextTick()
    preview.value?.focus()
    preview.value?.select()
    status.value = "Select and copy the request below, then paste it into your email."
  }
}
</script>

<template>
  <section class="page-shell contact-page" aria-labelledby="contact-title">
    <header class="page-heading contact-heading">
      <p class="eyebrow">Orders & enquiries</p>
      <h1 id="contact-title">Contact us</h1>
      <p>Tell us what you have in mind. Request an item, share a purchase order, or ask us a question.</p>
    </header>

    <div class="contact-layout">
      <form ref="formElement" class="account-card contact-form" @submit.prevent="prepareEmail">
        <div class="account-card__heading">
          <h2>Start a conversation</h2>
          <p>We’ll prepare an email for you to review and send. No account is needed.</p>
        </div>
        <div v-if="!contactEmail" class="form-alert form-alert--error" role="alert">Email requests are temporarily unavailable. Please check back shortly.</div>
        <div class="form-field">
          <label for="contact-type">How can we help?</label>
          <select id="contact-type" v-model="form.requestType">
            <option value="items">Item order request</option>
            <option value="purchase-order">Purchase order</option>
            <option value="question">General enquiry</option>
          </select>
        </div>
        <div class="form-row">
          <div class="form-field"><label for="contact-name">Your name</label><input id="contact-name" v-model.trim="form.name" autocomplete="name" maxlength="120" required @input="($event.target as HTMLInputElement).setCustomValidity('')" /></div>
          <div class="form-field"><label for="contact-email">Your email</label><input id="contact-email" v-model.trim="form.email" type="email" autocomplete="email" maxlength="254" required /></div>
        </div>
        <div class="form-field"><label for="contact-organization">Company or organization <span>(optional)</span></label><input id="contact-organization" v-model.trim="form.organization" autocomplete="organization" maxlength="160" /></div>
        <div v-if="form.requestType === 'purchase-order'" class="form-field">
          <label for="contact-po">Purchase order reference <span>(optional)</span></label>
          <input id="contact-po" v-model.trim="form.purchaseOrder" maxlength="100" aria-describedby="contact-attachment-note" />
          <p id="contact-attachment-note" class="contact-help">Attach your purchase order document to the email draft before sending it.</p>
        </div>
        <fieldset v-if="form.requestType !== 'question'" class="contact-destination">
          <legend>Delivery location <span>(optional)</span></legend>
          <div class="form-row">
            <div class="form-field"><label for="contact-destination">City, province/state & postal code</label><input id="contact-destination" v-model.trim="form.destination" maxlength="160" placeholder="For a delivery estimate" /></div>
            <div class="form-field"><label for="contact-country">Country</label><select id="contact-country" v-model="form.country"><option value="">Select a country</option><option value="Canada">Canada</option><option value="United States">United States</option></select></div>
          </div>
        </fieldset>

        <div v-if="bag.items.length" class="contact-bag-choice">
          <label><input v-model="includeBag" type="checkbox" /> Include {{ bag.itemCount }} {{ bag.itemCount === 1 ? 'item' : 'items' }} from my bag</label>
          <RouterLink :to="{ name: 'bag' }" class="text-link">Edit bag</RouterLink>
        </div>
        <div v-if="requestedItems.length" class="contact-items" aria-label="Requested items">
          <div v-for="(item, index) in requestedItems" :key="index" class="contact-item">
            <div><strong>{{ item.name }}</strong><small v-if="item.variation">{{ item.variation }}</small><small v-if="item.sku">SKU: {{ item.sku }}</small></div>
            <span>Qty {{ item.quantity }}</span>
          </div>
          <p>For different quantities or additional items, include the details below.</p>
        </div>
        <div class="form-field">
          <label for="contact-details">{{ requestedItems.length ? 'Additional details' : 'Your request' }} <span v-if="requestedItems.length">(optional)</span></label>
          <textarea id="contact-details" v-model="form.details" rows="5" maxlength="4000" :required="!requestedItems.length" placeholder="Include item names, sizes, colours, quantities and any questions." @input="($event.target as HTMLTextAreaElement).setCustomValidity('')" />
        </div>
        <button class="button button--primary button--wide" type="submit" :disabled="!contactEmail">Prepare email request <span aria-hidden="true">→</span></button>
        <p class="contact-help">You’ll send the request from your email app. Payment is arranged after we confirm your quote.</p>

        <section v-if="prepared" class="contact-preview" aria-labelledby="contact-preview-title" aria-live="polite">
          <h3 id="contact-preview-title" ref="previewHeading" tabindex="-1">Your email is ready to review</h3>
          <p v-if="needsCopy">This request is too long for some email apps. Copy it below, open an email and paste the complete request before sending.</p>
          <p v-else>Open the draft in your email app, review the details and send it there. This page has not sent your request.</p>
          <p v-if="form.requestType === 'purchase-order'">Remember to attach your purchase order document.</p>
          <p class="contact-recipient">To: <strong>{{ contactEmail }}</strong></p>
          <div class="contact-actions">
            <button v-if="needsCopy" class="button button--primary" type="button" @click="copyRequest">Copy request</button>
            <a class="button" :class="needsCopy ? 'button--secondary' : 'button--primary'" :href="needsCopy ? shortEmailUrl : emailUrl">{{ needsCopy ? 'Open email app' : 'Open email draft' }} <span aria-hidden="true">↗</span></a>
            <button v-if="!needsCopy" class="text-button" type="button" @click="copyRequest">Copy request instead</button>
          </div>
          <p v-if="status" role="status" class="contact-help">{{ status }}</p>
          <details ref="previewDetails" :open="needsCopy">
            <summary>View or copy the full request</summary>
            <label for="contact-preview-body" class="sr-only">Prepared email text</label>
            <textarea id="contact-preview-body" ref="preview" :value="draft.body" readonly rows="12" />
          </details>
        </section>
      </form>

      <aside class="contact-aside" aria-label="Ordering by email">
        <p class="eyebrow">A little more personal</p>
        <h2>Your next order<br />starts here.</h2>
        <p>From a single item to a business purchase order, we’ll help you put the details together.</p>
        <ol class="contact-steps">
          <li><span>01</span><div><h3>Tell us what you need</h3><p>Include your items, options and quantities, or attach your purchase order in your email app.</p></div></li>
          <li><span>02</span><div><h3>We confirm the details</h3><p>We’ll reply with availability and a quote including shipping and applicable taxes.</p></div></li>
          <li><span>03</span><div><h3>Arrange your order</h3><p>Review and accept the quote before following the payment instructions in our reply.</p></div></li>
        </ol>
        <div v-if="contactEmail" class="contact-direct"><p>Prefer to write directly?</p><a :href="directEmailUrl">{{ contactEmail }} <span aria-hidden="true">↗</span></a></div>
        <RouterLink class="text-link" :to="{ name: 'home', hash: '#catalog' }">Explore the catalogue <span aria-hidden="true">→</span></RouterLink>
      </aside>
    </div>
  </section>
</template>
