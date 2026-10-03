import { describe, expect, it } from "vitest"
import { bagRequestItems, buildContactDraft, contactMailto, validContactEmail, type ContactForm } from "../src/contact"
import type { BagItem } from "../src/types/bag"

const form: ContactForm = {
  requestType: "purchase-order", name: "Avery Stone", email: "avery@example.com",
  organization: "Example Studio", purchaseOrder: "PO-100", destination: "Calgary, AB",
  country: "Canada", details: "Please confirm availability & delivery.\nWe need two sizes.",
}

describe("Email order requests", () => {
  it("carries each bag variation and quantity without treating displayed prices as a quote", () => {
    const items = [
      { name: "Poster", slug: "poster", variation: "24x36 / Black", quantity: 2, price: 68.99 },
      { name: "Poster", slug: "poster", variation: "18x24 / Blue", quantity: 3, price: 49.99 },
    ] as BagItem[]
    const draft = buildContactDraft(form, bagRequestItems(items))
    expect(draft.subject).toContain("Purchase order request")
    for (const value of ["PO-100", "Example Studio", "24x36 / Black", "18x24 / Blue", "Quantity requested: 2", "Quantity requested: 3", "https://organicemperor.com/products/poster"])
      expect(draft.body).toContain(value)
    expect(draft.body).not.toContain("68.99")
    expect(draft.body).toContain("applicable taxes before payment")
  })

  it("encodes customer text as body content without allowing additional mail headers", () => {
    const draft = buildContactDraft({ ...form, details: "A&B?cc=other@example.com\n🧠 <script>alert(1)</script>" }, [])
    const url = new URL(contactMailto("support@organicemperor.com", draft.subject, draft.body))
    expect(url.protocol).toBe("mailto:")
    expect(url.pathname).toBe("support@organicemperor.com")
    expect([...url.searchParams.keys()]).toEqual(["subject", "body"])
    expect(url.searchParams.get("body")).toContain("A&B?cc=other@example.com\r\n🧠 <script>alert(1)</script>")
  })

  it("rejects malformed recipients and flattens line breaks in the subject", () => {
    for (const email of ["", "support@example.com?bcc=bad@example.com", "support@example.com\r\nBcc:bad@example.com", "a@example.com,b@example.com", "mailto:support@example.com"])
      expect(contactMailto(email, "Request", "Body")).toBe("")
    expect(validContactEmail(" support@organicemperor.com ")).toBe("support@organicemperor.com")
    const url = new URL(contactMailto("orders+shop@example.com", "Order\r\nBcc:other@example.com"))
    expect(decodeURIComponent(url.pathname)).toBe("orders+shop@example.com")
    expect(url.searchParams.get("subject")).not.toMatch(/[\r\n]/)
    expect(url.searchParams.has("bcc")).toBe(false)
  })
})
