# Storefront cart: CSRF origin rejection

The bag error `Origin checking failed - https://organicemperor.com does not match
any trusted origins` means the running API does not trust that exact storefront
origin. This check runs before the cart update. A valid CSRF token or CORS header
does not override it. See [Django's CSRF origin setting](https://docs.djangoproject.com/en/5.2/ref/settings/#csrf-trusted-origins).

The current `backend/config/settings.py` defaults already include the storefront.
An explicit `CSRF_TRUSTED_ORIGINS` environment variable replaces those defaults.
The backend ZIP deliberately excludes `.env`, so uploading it does not update
the live environment. An older loaded process can also retain old settings.

## Apply the production configuration

In the existing production API environment (the server `.env` or Passenger
environment configuration), append these exact origins to the existing
comma-separated `CSRF_TRUSTED_ORIGINS` and `CORS_ALLOWED_ORIGINS` values:

```text
https://organicemperor.com
https://www.organicemperor.com
```

Keep the existing Archives, admin and any other intentionally configured origins.
Do not replace the list with the local `.env` values. Origins have the scheme
and hostname only: no trailing slash, `/bag` path or quotes around individual
comma-separated entries. Keep `DJANGO_DEBUG=False` in production.

In the deployment's Python environment and backend directory, inspect only the
effective origin settings:

```sh
python manage.py shell -c "from django.conf import settings; print('CSRF_TRUSTED_ORIGINS:', settings.CSRF_TRUSTED_ORIGINS); print('CORS_ALLOWED_ORIGINS:', settings.CORS_ALLOWED_ORIGINS)"
```

Passenger environment variables take precedence over `.env` because dotenv is
loaded with `override=False`. Update the configuration that actually supplies
the settings, then restart the existing Passenger application through the
hosting panel. A frontend rebuild alone does not apply this change. If the
running code differs from the repository, deploy the matching backend first.

## Verify the loaded release

Refresh the live bag in the signed-in browser and perform one intended quantity
update. The API `/api/v1/commerce/cart/items/` request must succeed and the bag
must agree with the server after a reload. Keep the response status and any
error detail for diagnosis; do not share session cookies or CSRF tokens.

Token validation, authenticated customer access, secure cookies and origin
checks remain enabled. The regression suite demonstrates that adding the exact
storefront origin permits authenticated updates, while unknown origins,
missing/invalid tokens and unauthenticated requests still fail:

```sh
python manage.py test commerce.test_csrf
```

Production environment changes and Passenger restart must be verified on the
server. Local regression results do not establish that the live configuration
has changed.
