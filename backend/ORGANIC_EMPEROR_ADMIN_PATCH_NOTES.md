# Organic Emperor Django Admin Theme

## Included changes

- Adds the supplied Organic Emperor wordmark and crown/leaf brand emblem.
- Applies a responsive green, gold, cream, and charcoal interface.
- Supports Django's light, dark, and automatic theme modes.
- Styles the dashboard, login, forms, tables, filters, buttons, messages, and footer.
- Adds working shortcuts for Products, Categories, and the public storefront.
- Registers project templates and source static assets.
- Enables WhiteNoise compressed static-file delivery in production.

## Deploy

Copy the included files into the backend while preserving their paths, then run:

```bash
python manage.py collectstatic --noinput
python manage.py check --deploy
```

Restart the Django/Gunicorn application after `collectstatic` completes.

If the admin is served by a separate web-server rule, ensure `/static/` resolves to the backend's `staticfiles` directory. The expected filesystem path is the `STATIC_ROOT` configured in `config/settings.py`.
