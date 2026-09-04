# OrganicEmperor.com Webstore

Phase-one foundation for replacing WooCommerce with Django REST Framework, MYSQL, Vue 3, Pinia, TypeScript and CSS.

## Local backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Local frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Domain map

- `organicemperor.com`: built Vue storefront (`frontend/dist`)
- `api.organicemperor.com`: Django application and `/api/v1/` endpoints
- `admin.organicemperor.com`: reverse proxy to the same Django application `/admin/`
- `organicarchives.organicemperor.com`: Organic Archives Vue application (`frontend/dist-archives`)

## Organic Archives

The editorial archive provides a numbered feed, category filters, search, and
article pages with images and videos. Editors publish articles, news releases,
and updates through Django Admin, including drafts and scheduled publication.

Run `npm run dev:archives` or `npm run build:archives` from `frontend` for the
separate archive application. See [publishing, local preview, and deployment
instructions](deployment/ORGANIC_ARCHIVES.md).

## Available API routes

- `GET /health/`
- `GET /api/v1/categories/`
- `GET /api/v1/products/`
- `GET /api/v1/products/?search=balm&category=shave-care`
- `GET /api/v1/products/<slug>/`
- `GET /api/v1/archives/posts/`
- `GET /api/v1/archives/posts/<slug>/`
- `GET /api/v1/auth/csrf/`
- `POST /api/v1/auth/register/`
- `POST /api/v1/auth/sign-in/`
- `POST /api/v1/auth/sign-out/`
- `GET|PATCH /api/v1/auth/me/`
- `POST /api/v1/auth/password/`
- `GET /api/v1/commerce/cart/`
- `PUT /api/v1/commerce/cart/items/`
- `POST /api/v1/commerce/cart/merge/`
- `GET /api/v1/commerce/shipping-rates/`
- `POST /api/v1/commerce/checkout/quote/`
- `POST /api/v1/commerce/checkout/paypal/create/`
- `POST /api/v1/commerce/checkout/paypal/capture/`
- `GET /api/v1/commerce/orders/`
- `GET /api/v1/commerce/orders/<number>/`
- `POST /api/v1/commerce/webhooks/paypal/`

## Customer authentication

Customer accounts use Django's server-side sessions and CSRF protection. The
frontend sends requests with credentials enabled and obtains a CSRF token before
every unsafe account request. Passwords and authentication tokens are never
written to browser storage.

Production must set `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the
exact deployed frontend origins. HTTPS is required for the secure session and
CSRF cookies when `DJANGO_DEBUG=False`.

## Commerce configuration

Checkout uses PayPal and CAD-denominated flat-rate shipping to Canada and the
United States. Migration `commerce.0005_configure_initial_shipping_rates`
activates the agreed initial rates: $15 CAD to Canada and $25 CAD to the United
States. Both rates remain editable in Django Admin.
Production checkout remains blocked by `UnavailableTaxAdapter` until a real tax
provider is connected.

PayPal requires `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`,
and `PAYPAL_MODE`. Schedule `python manage.py release_expired_checkout_reservations`
every five minutes so abandoned PayPal checkouts return reserved inventory.

Import a WooCommerce export with:

```bash
python manage.py import_woocommerce_csv products.csv --dry-run
python manage.py import_woocommerce_csv products.csv
```

Use `--image-base-dir /path/to/images` to import matching local image files
without downloading untrusted remote URLs.

## Next milestone

Configure PayPal Sandbox credentials and the sandbox-only zero-tax adapter, then run an end-to-end acceptance test.
Production tax remains blocked until the provider milestone is completed.
