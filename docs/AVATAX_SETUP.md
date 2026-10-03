# Connect checkout to Avalara AvaTax

The checkout already has an AvaTax adapter. HTTP 401 means AvaTax rejected its
authentication. The local `backend/.env` currently has example credentials and
an example ship-from address; they cannot authenticate or calculate real tax.
The live server has its own configuration, which must also be updated.

## Create the account and company

1. Open [Avalara's AvaTax developer trial page](https://developer.avalara.com/freeTrial/)
   and select **Start AvaTax trial**. Complete signup using the business owner's
   email. For real purchases, obtain a production AvaTax account with API access
   through Avalara. A developer trial is for testing the integration.
2. Confirm the account's environment in the welcome message or with Avalara.
   [Sandbox and production have separate accounts and credentials](https://developer.avalara.com/erp-integration-guide/authentication-in-avatax/sandbox-vs-production/).
   Sandbox portal: <https://sandbox.admin.avalara.com>. Production portal:
   <https://admin.avalara.com>. Use the portal matching the account you received.
3. Complete the company setup and activate the company. Set its company code to
   `ORGANICEMPEROR` if available, or copy the code you actually chose. The adapter
   requires that exact company code, rather than the display name or numeric
   company ID. Avalara documents [company codes](https://developer.avalara.com/erp-integration-guide/designing/company-code/).
4. Configure the company's actual tax collection jurisdictions and registrations,
   and verify taxability for the catalog SKUs, including variation SKUs. Use the
   actual fulfilment ship-from address. The customer's checkout address is the
   ship-to address and must not be copied into the ship-from settings.
5. Obtain the numeric **account ID** and **license key** from the same environment.
   This adapter uses account ID/license key authentication, rather than your
   portal email/password. Avalara's [account integration instructions](https://developer.avalara.com/avatax/logins/)
   describe where to obtain the key. Generating a replacement key revokes the
   old one, so use an existing key if other integrations already depend on it.

## Enter the private backend settings

Fill the empty values below in the private backend `.env`. Do not paste keys
into chat or commit them. `AVATAX_COMPANY_CODE` must match the activated company.
`AVATAX_ENVIRONMENT` must match the issued credentials; keep it `sandbox` only
when using a sandbox account for testing.

```dotenv
COMMERCE_TAX_ADAPTER=commerce.tax.AvaTaxAdapter
COMMERCE_ALLOW_ZERO_TAX=False
AVATAX_ENVIRONMENT=sandbox
AVATAX_ACCOUNT_ID=
AVATAX_LICENSE_KEY=
AVATAX_COMPANY_CODE=ORGANICEMPEROR
AVATAX_ORIGIN_LINE1=
AVATAX_ORIGIN_CITY=
AVATAX_ORIGIN_REGION=
AVATAX_ORIGIN_POSTAL_CODE=
AVATAX_ORIGIN_COUNTRY=CA
```

Region and country use the appropriate codes for the fulfilment origin, such as
`AB` and `CA` for an Alberta origin. Enter the origin's actual street and postal
code. Do not retain `your-...` sample values.

For production checkout, use production credentials with
`AVATAX_ENVIRONMENT=production` in the live API configuration. Local `.env`
changes are not uploaded by backend packaging. Passenger environment variables
take precedence over `.env`; update the source actually supplying these values,
then restart the existing Passenger application. Keep keys on the backend.

## Verify before a purchase

From the repository root on Windows:

```powershell
.\.org_env\Scripts\python.exe backend/manage.py check_avatax --local-only
.\.org_env\Scripts\python.exe backend/manage.py check_avatax
```

On the server, from the deployed backend directory and Python environment:

```sh
python manage.py check_avatax --local-only
python manage.py check_avatax
```

The local check validates loaded settings without network requests. The full
check makes authenticated GET requests to the AvaTax ping and company APIs. It
does not transmit a customer address, create a tax transaction, change inventory
or start a payment. Its output excludes keys and account details. A successful
check verifies authentication and access to the configured active company;
it does not verify registrations, product taxability or a calculated amount.

Then use **Review order total** in a test checkout. Verify that the API quote
has `tax_provider=avalara-avatax` and the expected tax for the company's configured
products and destination. Verify its saved checkout session in Django Admin has
a non-empty tax reference. Verify the CAD total includes
items, shipping and tax. Do not assume every destination owes tax or substitute
a fixed rate. Complete payment acceptance with PayPal sandbox credentials.

## Diagnose a failed check

- Example or missing setting: fill the named setting in the effective backend
  environment. The command stops before contacting Avalara.
- Authentication false or HTTP 401: check the account ID, license key and
  environment as a matching set. A portal password is not a license key.
  Stop repeated retries until the configuration is corrected.
- Company missing or inactive: verify the exact company code in that account
  and activate the company in Avalara.
- HTTP 403: confirm the account's API access and company permissions with Avalara.
- Network failure: check the server can reach the selected HTTPS AvaTax endpoint.

Share only the command's sanitized status/error when asking for help.

## What this integration records

The adapter calculates uncommitted `SalesOrder` quotes with authoritative CAD
product lines and the existing freight code `FR020100`. It does not record the
final paid sale as a committed AvaTax invoice. Production use also needs an
agreed process for reporting paid sales and refunds; a successful connection
check does not establish that filing workflow. See the existing
[PayPal and AvaTax acceptance notes](../PAYPAL_AVATAX_DEPLOYMENT_NOTES.md).
