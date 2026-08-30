# Organic Emperor PayPal Sandbox and AvaTax setup — v1.5.0

The checkout remains CAD-denominated. Shipping rates stay database-managed and
are not changed by this patch.

## PayPal Sandbox

Create or select a Sandbox REST app in the PayPal Developer Dashboard. Add this
webhook URL to that same app:

`https://api.organicemperor.com/api/v1/commerce/webhooks/paypal/`

Subscribe to `PAYMENT.CAPTURE.COMPLETED`, then add the sandbox values to the
private backend `.env` file:

```dotenv
PAYPAL_MODE=sandbox
PAYPAL_CLIENT_ID=your-sandbox-client-id
PAYPAL_CLIENT_SECRET=your-sandbox-client-secret
PAYPAL_WEBHOOK_ID=your-sandbox-webhook-id
```

Never commit the client secret or use live credentials during acceptance tests.

## Avalara AvaTax Sandbox

Create an AvaTax sandbox company configured for the jurisdictions in which the
business is registered to collect tax. Add the sandbox credentials and the
real ship-from address to the private backend `.env` file:

```dotenv
COMMERCE_TAX_ADAPTER=commerce.tax.AvaTaxAdapter
COMMERCE_ALLOW_ZERO_TAX=False

AVATAX_ENVIRONMENT=sandbox
AVATAX_ACCOUNT_ID=your-sandbox-account-id
AVATAX_LICENSE_KEY=your-sandbox-license-key
AVATAX_COMPANY_CODE=ORGANICEMPEROR
AVATAX_ORIGIN_LINE1=your-ship-from-street
AVATAX_ORIGIN_CITY=your-ship-from-city
AVATAX_ORIGIN_REGION=AB
AVATAX_ORIGIN_POSTAL_CODE=your-postal-code
AVATAX_ORIGIN_COUNTRY=CA
```

The adapter creates uncommitted `SalesOrder` calculations, passes each product
as an authoritative CAD line, and passes shipping with AvaTax freight code
`FR020100`. Missing credentials, bad responses, and network errors block
checkout instead of guessing tax.

## Deploy and verify

```bash
cd backend
python manage.py check
python manage.py test accounts commerce
python manage.py shell -c "from commerce.tax import AvaTaxAdapter; print(AvaTaxAdapter().base_url)"
```

The final command must print the sandbox hostname. Restart Passenger, create a
new checkout quote, and verify the response contains:

- `tax_provider`: `avalara-avatax`
- a non-empty `tax_reference`
- the expected address-dependent `tax_cad`

Then complete one PayPal Sandbox purchase using a Personal sandbox buyer. Verify
exactly one order, one capture ID, one converted cart, one inventory decrement,
and one verified webhook event in Django Admin.

Do not change either provider to production until the business tax registrations/nexus settings and the process for recording paid sales in AvaTax have been reviewed.

This version calculates checkout tax; automated filing transaction commitment is a separate production-readiness milestone.
