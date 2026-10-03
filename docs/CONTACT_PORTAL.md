# Storefront contact and order requests

The public `/contact` page prepares item requests, purchase order requests and
general enquiries addressed to `support@organicemperor.com`. Customers review
the prepared email, attach any purchase order document in their own email app,
and send it themselves. Preparing a request does not submit an order or take
payment. Availability, prices, shipping and applicable taxes are confirmed in
the store's reply before payment is arranged.

Customers can reach the page through the announcement, desktop header, footer,
product details, shopping bag, bag drawer and checkout. Bag requests carry the
chosen options and quantities. Product requests include the selected option
and SKU; products with variations require an option selection before the link
appears. The page is available to guests.

The recipient is defined in `frontend/src/contact.ts`. The optional public
`VITE_CONTACT_EMAIL` build setting overrides it. A malformed address disables
email preparation. No SMTP credentials or backend changes are required. Verify
the support mailbox exists and is monitored before publishing the storefront.

Long requests use a copy/paste fallback rather than relying on email apps to
accept an oversized `mailto:` URL. The full request remains visible and
copyable if the browser denies clipboard access or no email app opens. Customers
can also email the displayed support address directly. Contact details and
request text are held only in page memory, not saved in browser storage.

## Validate and package

From the repository root:

```powershell
npm --prefix frontend test -- tests/contact.test.ts tests/ContactView.test.ts tests/ProductDetailView.test.ts tests/bag.test.ts
.\.org_env\Scripts\python.exe scripts/package_frontends.py
.\.org_env\Scripts\python.exe scripts/package_backend.py
```

The frontend packaging command type-checks and builds both frontends, validates their
asset references and produces `dist.zip` and `dist-archives.zip`. Deploy the
storefront's matching index and assets together. `backend.zip` contains matching
generated HTML for the product pages served by the SEO backend; deploy that
matching HTML with the storefront release so product pages discover the new
assets and contact links. Private configuration is excluded. Publishing is a
separate step.

Check `/contact` on desktop and mobile, prepare a short request and a long
purchase order, and confirm the recipient, selected options and quantities.
Email delivery itself requires a customer to send the email; an opened draft
is not evidence that the support inbox received a request.
