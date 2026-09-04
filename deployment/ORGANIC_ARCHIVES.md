# Organic Archives

Organic Archives is a separate Vue application built from the existing frontend
dependencies. The store keeps its current entry point and build. Content lives in
the existing Django database and media storage, and publishing uses Django Admin.

## Publish a post

1. Sign in at `https://admin.organicemperor.com/admin/archives/post/` using a staff
   account with Archives post and post block add/change permissions.
2. Add a title, unique slug, post type (Article, News release, or Update), excerpt,
   and public author name. Topic and cover image are optional; cover images require
   descriptive alternative text.
3. Add content sections under Post blocks. Use the position field to order them.
   Supported sections: plain text, heading, quote, uploaded image, uploaded video,
   and a YouTube or public Vimeo video URL. Blank lines in text create paragraphs.
   HTML is intentionally displayed as text. Captions are optional; provide a
   transcript in a text section for videos with spoken content.
4. Save as Draft while editing. To publish, select Published and set a publication
   date/time. A future date schedules release; no background job is required.
   The Django admin shows its configured timezone (America/Edmonton).
5. After publication, the View on site link opens the post. Drafts and future posts
   are unavailable on the public API, including to logged-in staff. Return a post
   to Draft to withdraw it. Keep published slugs stable to preserve incoming links.

Images use Django/Pillow validation. Uploaded videos accept MP4 and WebM, up to
100 MB. Configure the web host's upload limit accordingly and serve uploaded files
as non-executable media. MP4 with H.264/AAC is a broadly compatible encoding.
Only supported HTTPS YouTube/Vimeo URLs can become embedded players. External
players may make third-party requests when an article is opened.

## Deploy on the existing Organic Emperor hosting

Deploy backend first, then frontend. Both are required; uploading the frontend
alone cannot provide persistent publishing. The Django application cannot run in
the Cloudflare Workers runtime used by Sites, so retain the existing Python host.

1. Release the updated backend with the new `archives` app.
2. With the production backend environment loaded, run:

   ```sh
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py check
   ```

   Restart the existing Passenger/WSGI application using the hosting panel.
   Existing database and media backup procedures should include archives content.
3. If production sets `CORS_ALLOWED_ORIGINS` explicitly, ensure it includes
   `https://organicarchives.organicemperor.com` alongside existing origins.
   The default already includes it. Publishing occurs on the admin origin;
   readers do not need cross-origin session cookies.
4. From `frontend`, run `npm run build:archives`. The output is `frontend/dist-archives`.
   Its default API is `https://api.organicemperor.com/api/v1`. For another API,
   set `VITE_ARCHIVES_API_BASE_URL` in the build environment (including `/api/v1`).
   Never enable `VITE_ARCHIVES_DEMO` in production.
5. Create the `organicarchives.organicemperor.com` subdomain in the existing hosting
   panel, with a separate document root. Point its DNS record at that host and
   issue an HTTPS certificate. Upload the **contents** of `dist-archives`, including
   `.htaccess`, into this root. Do not replace the storefront's document root.
   The included Apache rewrite rule serves `index.html` for article deep links.
   On Nginx, use `try_files $uri $uri/ /index.html;` in the site location.
6. Check the subdomain homepage, a direct `/posts/<slug>` URL, category/search
   results, and image/video playback. Publish a real post through Django Admin.
   An empty production archive displays an honest empty state; sample posts are
   never installed through migrations.

The public endpoints are read-only:

- `GET /api/v1/archives/posts/?kind=article&search=ingredients&page=1`
- `GET /api/v1/archives/posts/<slug>/`

The feed has 15 posts per page, ordered newest first. Post metadata is updated in
the browser; this Vue SPA does not provide server-rendered article metadata for
social crawlers that do not execute JavaScript.

## Local development

Use a separate database for previews. In PowerShell from the repository root:

```powershell
$env:DJANGO_DEBUG = 'True'
$previewDatabase = (Join-Path (Get-Location) 'backend/.archives-preview.sqlite3').Replace('\', '/')
$env:DATABASE_URL = "sqlite:///$previewDatabase"
.org_env/Scripts/python.exe backend/manage.py migrate
.org_env/Scripts/python.exe backend/manage.py seed_archives_preview
.org_env/Scripts/python.exe backend/manage.py runserver 127.0.0.1:8001
```

In another terminal, from `frontend`:

```powershell
$env:VITE_ARCHIVES_DEMO = 'true'
npm run dev:archives
```

Open `http://127.0.0.1:5174`. Requests to `/api` and `/media` proxy to port 8001.
The sample seeder refuses to run outside the specifically named preview SQLite
database and requires DEBUG. To test publishing locally, create a superuser in
that same preview environment and open `http://127.0.0.1:8001/admin/` directly.
The preview header's publisher link intentionally targets the real admin domain.

Validation (with the development backend environment above):

```powershell
.org_env/Scripts/python.exe backend/manage.py test archives
npm --prefix frontend run build:archives
npm --prefix frontend run build
```
