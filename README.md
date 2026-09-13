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

## Backend deployment ZIP

Create a clean backend archive from the repository root with:

```bash
python scripts/package_backend.py
```

The script uses Git's `.gitignore` rules, includes tracked files and new
non-ignored source files, and excludes local databases, environment files,
uploads, collected static files, caches, logs, and ZIP files. It writes
`backend.zip` with the `backend/` directory at the archive root, atomically
replacing the previous deployment archive, validating the result, and printing
its SHA-256 checksum. Custom output names remain protected; use
`--output NAME.zip`, adding `--force` only when replacing that custom file.

Package both frontend deployments with:

```bash
python scripts/package_frontends.py
```

This runs a shared type check, rebuilds both Vite applications, and atomically
replaces `dist.zip` and `dist-archives.zip`. Each archive contains the contents
of its corresponding distribution directory at the ZIP root, including the
required `.htaccess` and `index.html`, ready to extract directly into its web
document root. Use `--skip-build` only when the existing distribution folders
are already current.

## Domain map

- `organicemperor.com`: built Vue storefront (`frontend/dist`)
- `api.organicemperor.com`: Django application and `/api/v1/` endpoints
- `admin.organicemperor.com`: reverse proxy to the same Django application `/admin/`
- `organicarchives.organicemperor.com`: OrganicArchives Vue application (`frontend/dist-archives`)

## OrganicArchives

The editorial archive provides a numbered feed, category filters, search, and
article pages with images and videos. Editors publish articles, news releases,
and updates through Django Admin, including drafts and scheduled publication.

Running `python manage.py migrate` creates an `Organic Archives Publishers`
group scoped to Posts and Post Blocks. After creating a normal user and setting
its password, provision the exact staff-only scope with:

```bash
python manage.py assign_archives_publisher USERNAME
```

The command removes superuser status, other groups, and direct permissions so
the account cannot access customer, catalogue, commerce, or authentication
tables in Django Admin.

Readers use ordinary non-staff customer accounts. They can register or sign in
from the Archives `/reader` page, subscribe to an in-app new-post notification
feed, like a published post once, and leave plain-text comments. They never
receive Django Admin or post-editing permissions. Publishers can moderate
comments, likes, and subscriptions from the Organic Archives section of Admin.

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
- `GET /api/v1/archives/posts/<slug>/engagement/`
- `PUT|DELETE /api/v1/archives/posts/<slug>/like/`
- `POST /api/v1/archives/posts/<slug>/comments/`
- `GET|PUT|DELETE /api/v1/archives/subscription/`
- `GET /api/v1/archives/notifications/`
- `POST /api/v1/archives/notifications/read/`
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
