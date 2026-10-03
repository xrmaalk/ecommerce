import type { BagItem } from "./types/bag"

// Public inbox only. Override with VITE_CONTACT_EMAIL when building a storefront.
const defaultContactEmail = "support@organicemperor.com"
export function validContactEmail(value: string): string {
  const email = value.trim()
  return /^[A-Z0-9.!#$%&'*+/=^_`{|}~-]+@[A-Z0-9](?:[A-Z0-9.-]*[A-Z0-9])?\.[A-Z]{2,}$/i.test(email)
    ? email : ""
}
export const contactEmail = validContactEmail(import.meta.env.VITE_CONTACT_EMAIL || defaultContactEmail)

export type RequestType = "items" | "purchase-order" | "question"
export interface ContactForm {
  requestType: RequestType
  name: string
  email: string
  organization: string
  purchaseOrder: string
  destination: string
  country: string
  details: string
}
export interface RequestedItem {
  name: string
  slug: string
  variation: string
  sku?: string
  quantity: number
}

export function bagRequestItems(items: BagItem[]): RequestedItem[] {
  return items.map(({ name, slug, variation, quantity }) => ({ name, slug, variation, quantity }))
}

const line = (value: string) => value.replace(/[\r\n\u0000-\u001f\u007f]+/g, " ").trim()
export function buildContactDraft(form: ContactForm, items: RequestedItem[]) {
  const subjects: Record<RequestType, string> = {
    items: "OrganicEmperor - Item order request",
    "purchase-order": "OrganicEmperor - Purchase order request",
    question: "OrganicEmperor - Customer enquiry",
  }
  const subject = subjects[form.requestType]
  const body = [
    subject, "",
    `Name: ${line(form.name)}`,
    `Reply email: ${line(form.email)}`,
    ...(form.organization.trim() ? [`Company / organization: ${line(form.organization)}`] : []),
    ...(form.requestType === "purchase-order" && form.purchaseOrder.trim()
      ? [`Purchase order reference: ${line(form.purchaseOrder)}`] : []),
    ...(form.destination.trim() ? [`Delivery location: ${line(form.destination)}`] : []),
    ...(form.country ? [`Country: ${line(form.country)}`] : []),
    ...(items.length ? ["", "Requested items:", ...items.flatMap((item, index) => [
      `${index + 1}. ${line(item.name)}`,
      ...(item.variation ? [`   Option: ${line(item.variation)}`] : []),
      ...(item.sku ? [`   SKU: ${line(item.sku)}`] : []),
      `   Quantity requested: ${item.quantity}`,
      `   Product: https://organicemperor.com/products/${encodeURIComponent(item.slug)}`,
    ])] : []),
    ...(form.details.trim() ? ["", "Request details:", form.details.trim().replace(/\r\n?/g, "\n")] : []),
    "", "Please confirm availability, final prices, shipping and applicable taxes before payment.",
  ].join("\n")
  return { subject, body }
}

export function contactMailto(recipient: string, subject: string, body?: string): string {
  const email = validContactEmail(recipient)
  if (!email) return ""
  // Encoding the whole local part also prevents recipient/header injection.
  const path = email.split("@").map(encodeURIComponent).join("@")
  return `mailto:${path}?subject=${encodeURIComponent(line(subject))}` +
    (body === undefined ? "" : `&body=${encodeURIComponent(body.replace(/\r?\n/g, "\r\n"))}`)
}

// Some email applications truncate long mailto URLs. Copy/paste keeps long
// purchase orders complete instead of silently dropping requested items.
export const MAX_MAILTO_LENGTH = 1800
