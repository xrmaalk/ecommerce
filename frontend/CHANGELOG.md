# Version 1.4.1 — Initial shipping configuration

- Activated flat-rate shipping at $15 CAD for Canada and $25 CAD for the United States.
- Kept checkout and PayPal capture CAD-denominated to avoid exchange-rate ambiguity.
- Preserved the production tax safety gate while allowing the existing zero-tax adapter only when explicitly enabled for sandbox acceptance testing.

## Version 1.4.0 — Commerce and PayPal checkout foundation

- Added authenticated server-side carts with safe local-bag merging and server-authoritative prices.
- Added admin-configured flat-rate shipping for Canada and the United States.
- Added a provider-neutral tax adapter that blocks production checkout until a provider is configured.
- Added expiring checkout quotes and inventory reservation/release handling.
- Added PayPal Orders v2 creation, capture, amount validation, and verified idempotent webhooks.
- Added immutable customer orders, order items, protected order history, and confirmation views.
- Added a dry-run, repeat-safe WooCommerce CSV importer with optional local image imports.
- Added responsive checkout, PayPal button, order history, and dark-mode styling.

## Version 1.3.0 — Customer account authentication

- Added secure Django session authentication with explicit CSRF protection.
- Added customer registration, sign in, sign out, session restoration, profile editing, and password changes.
- Added rate limiting, password validation, normalized email login, and generic credential errors.
- Replaced the account placeholder with responsive sign-in, registration, and signed-in settings views.
- Added a protected account-settings route and authenticated header state.
- Included the staging storefront in the default CORS and CSRF origin configuration.
- Removed stale generated JavaScript copies so TypeScript remains the authoritative frontend source.

## Version 1.2.0 — Featured flame marker

- Replaced the obstructed featured text badge with a compact flame marker.
- Moved featured status to the upper-right corner with stable image layering.
- Preserved an accessible text label for screen readers and pointer tooltips.

## Version 1.1.0 — Featured badge and dark mode

- Corrected the featured badge stacking so it remains fully visible above every product image.
- Refined the badge into a high-contrast branded pill with stable spacing and typography.
- Added a header theme toggle with sun and moon icons.
- Uses the visitor's operating-system preference on first load and remembers manual selection.
- Added complete dark styling for the storefront, navigation, bag drawer, bag page, forms, and supporting views.

## Version 1.0.0 — Modular storefront refactor

- Replaced the monolithic application with routed views and reusable Vue components.
- Added a persistent Pinia shopping bag with validated browser storage.
- Added quantity increase, decrease, stock limits, removal, subtotal, drawer, and full bag view.
- Added accessible dialog focus handling, live announcements, keyboard controls, and reduced-motion support.
- Added abortable catalogue requests, typed API responses, error states, empty states, and debounced search.
- Applied the Organic Emperor emblem to navigation, hero, fallback art, empty states, favicon, and touch icon.
- Added responsive Organic Emperor design tokens and modular CSS files.
- Added account, privacy, returns, and not-found views so navigation does not end on blank routes.
- Added Apache history fallback and baseline security headers.
- Excluded dependencies and build caches from the delivery package.

Live checkout remains gated until real shipping amounts, PayPal credentials, and an automated tax provider are configured.
