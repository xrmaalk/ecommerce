# Version 1.2.0 — Featured flame marker

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

Checkout and account authentication are intentionally presented as pending until the corresponding secure Django endpoints are available.
