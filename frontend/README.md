# OrganicEmperor.com Storefront

A modular Vue 3 + TypeScript storefront connected to the OrganicEmperor.com Django catalogue API.

## Development

```bash
npm install
npm run dev
```

The active environment must define `VITE_API_BASE_URL`. Production currently targets `https://api.organicemperor.com/api/v1`.

## Validation and build

```bash
npm test
npm run typecheck
npm run build
```

All frontend tests live in `tests/`. Vitest discovers the `*.test.ts` files there,
and `npm run typecheck` checks them alongside the application sources.

Upload the contents of `dist/` to the frontend document root. The included `.htaccess` enables Vue Router history fallback and adds baseline browser security headers on Apache/DirectAdmin hosting.

## Structure

- `src/components/` — reusable branding, layout, catalogue, and bag UI
- `src/views/` — routed pages
- `src/stores/` — Pinia catalogue and persistent bag state
- `src/composables/` — reusable formatting and debounce helpers
- `src/styles/` — design tokens and scoped style modules
- `src/types/` — API and bag TypeScript contracts
- `tests/` — storefront and OrganicArchives frontend tests
- `src/seo.ts` — shared safe metadata updates; public HTML comes from Django

See [SEO deployment](../docs/SEO_DEPLOYMENT.md). Product and article sharing
requires the public-domain proxy rules and matching backend HTML shells as well
as the frontend build. A browser head update alone does not update crawler previews.

The shopping bag is persisted locally, validates restored data, respects inventory limits, and supports accessible increment, decrement, and removal controls. Checkout and authenticated account functions remain intentionally disabled until their secure Django endpoints are connected.

The colour theme follows the visitor's operating-system preference on first load. The header toggle switches between light and dark modes and saves the selection locally.
