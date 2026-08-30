# Organic Emperor Webstore

Phase-one foundation for replacing WooCommerce with Django REST Framework, PostgreSQL, Vue 3, Pinia, TypeScript and CSS.

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
- `organicarchives.organicemperor.com`: future Organic Archives Vue application

## Available API routes

- `GET /health/`
- `GET /api/v1/categories/`
- `GET /api/v1/products/`
- `GET /api/v1/products/?search=balm&category=shave-care`
- `GET /api/v1/products/<slug>/`

## Next milestone

Add customer authentication, server-side carts, orders, checkout sessions, payment webhooks and a WooCommerce CSV importer. Confirm the payment gateway and shipping/tax rules before implementing checkout.
