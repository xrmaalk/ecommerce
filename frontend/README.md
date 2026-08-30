# Organic Emperor Storefront

A modular Vue 3 + TypeScript storefront connected to the Organic Emperor Django catalogue API.

## Development

```bash
npm install
npm run dev
```

The active environment must define `VITE_API_BASE_URL`. Production currently targets `https://api.organicemperor.com/api/v1`.

## Validation and build

```bash
npm run typecheck
npm run build
```

Upload the contents of `dist/` to the frontend document root. The included `.htaccess` enables Vue Router history fallback and adds baseline browser security headers on Apache/DirectAdmin hosting.

## Structure

- `src/components/` — reusable branding, layout, catalogue, and bag UI
- `src/views/` — routed pages
- `src/stores/` — Pinia catalogue and persistent bag state
- `src/composables/` — reusable formatting and debounce helpers
- `src/styles/` — design tokens and scoped style modules
- `src/types/` — API and bag TypeScript contracts

The shopping bag is persisted locally, validates restored data, respects inventory limits, and supports accessible increment, decrement, and removal controls. Checkout and authenticated account functions remain intentionally disabled until their secure Django endpoints are connected.

The colour theme follows the visitor's operating-system preference on first load. The header toggle switches between light and dark modes and saves the selection locally.
