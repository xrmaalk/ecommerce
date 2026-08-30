# Version 1.0.0 — Modular storefront refactor

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

Checkout and account authentication are intentionally presented as pending until the corresponding secure Django endpoints are available.
