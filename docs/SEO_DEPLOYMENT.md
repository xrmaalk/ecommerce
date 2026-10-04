# Product and article sharing metadata

Public reader URLs remain `/products/<slug>` on OrganicEmperor and `/posts/<slug>`
on OrganicArchives. The current hosting plan cannot proxy requests to Django,
so the packaged `.htaccess` uses the crawler-only routing requested for this
installation. Normal browsers receive the styled Vue application on the public
frontend host. Recognised search and sharing crawlers receive a temporary 302
redirect to a fixed Django HTML endpoint. Canonical metadata continues to name
the public frontend URL.

Django uses the same public visibility filters and saved content as the reader.
Its Archives HTML includes the complete escaped article text before JavaScript,
plus the cover and ordered sections. The API article endpoint now serves a
standalone responsive reader with its own stylesheet at
`/site/archives/reader.css?v=<content-hash>`, so shared API links display correctly
without a frontend `/assets/` directory or Vue router. Navigation links return
to the canonical OrganicArchives site. The stylesheet is included in the
backend ZIP and served by Django directly; no new collectstatic step is needed.
It follows the browser's light/dark preference and preserves complete images.
Drafts, undated posts and future posts
remain excluded from all public detail, sharing-image and sitemap endpoints,
even for staff or a crawler user agent. Only authenticated, authorised publisher
sessions can use `/admin/archives/post/<id>/preview-data/`.

## Publisher preview host

Production **Publisher login** and draft-preview requests use
`https://api.organicemperor.com/admin/archives/post/`. Publishers must sign in on
that host; a session created on `admin.organicemperor.com` is a separate cookie.
An installation using another admin host must set `VITE_ARCHIVES_ADMIN_URL` to
that same login host and rebuild. Preview requests include credentials, disable
caching and never follow login redirects. Connection failures offer retry
rather than incorrectly telling an already signed-in publisher to log in.

## Build and deploy one matching release

```powershell
.\.org_env\Scripts\python.exe scripts/package_frontends.py
.\.org_env\Scripts\python.exe scripts/package_backend.py
```

Both frontends are rebuilt and typechecked, then every entry-document asset
reference and ZIP is validated. The backend package includes the generated
`site_shells/storefront.html` and `archives.html`, with bytes matching their
frontend entry documents. Deploy the backend and both frontends together,
retaining old hashed assets during the rollout. Explicitly overwrite the hidden
`.htaccess` file. No new dependencies or database migrations are required.

## Current routing

| Public request | Regular browser | Recognised crawler |
| --- | --- | --- |
| `/products/<slug>` | Storefront Vue shell | 302 to `https://api.organicemperor.com/site/storefront/products/<slug>` |
| `/posts/<slug>` | Archives Vue shell | 302 to `https://api.organicemperor.com/site/archives/posts/<slug>` |
| `/preview/<id>` | Private preview, publisher session required | Same protected preview; no crawler bypass |

The two crawler rules check a specific list of search and sharing user agents;
other agents stay on the frontend. User agents are routing hints, never
credentials. Both detail variants carry `Vary: User-Agent` and no-store headers
through `mod_setenvif` and `mod_headers`. The temporary redirects avoid declaring
that public article URLs have permanently moved to the API. `/assets/*` never
uses the SPA fallback, so a missing stylesheet or script returns 404.

Archives `/sitemap.xml` and `/robots.txt` redirect to their fixed Django
endpoints for everyone. The sitemap lists public canonical posts only. Trailing
slash article/product URLs first normalize on their frontend host with 301.
Malformed detail paths return 404; valid browser paths load the Vue reader,
which checks post/product availability through the public API.

This is a hosting workaround. A future hosting-supported reverse proxy or SSR
can serve initial metadata on the public URL for every visitor. Google's
[dynamic-rendering guidance](https://developers.google.com/search/docs/crawling-indexing/javascript/dynamic-rendering)
describes crawler-specific rendering as a workaround and requires equivalent
content. The repository preserves the same saved public content in both views.
Apache documents conditional header handling in
[mod_rewrite](https://httpd.apache.org/docs/2.4/mod/mod_rewrite.html).

## Verify after deployment

Check actual response headers without following redirects:

```powershell
curl.exe -sS -D - -o NUL -A "Mozilla/5.0" https://organicarchives.organicemperor.com/posts/REAL-PUBLIC-SLUG
curl.exe -sS -D - -o NUL -A "Googlebot/2.1" https://organicarchives.organicemperor.com/posts/REAL-PUBLIC-SLUG
```

The browser request should return 200 with the frontend shell; the crawler
request should return 302 with the fixed API URL in `Location`. Both should have
`Vary: User-Agent` and no-store. Open the canonical frontend article and verify
its actual stylesheet and module URLs load from the frontend `/assets/` path.
The direct API HTML endpoint is the crawler upstream and a styled reader for
shared API links. Its stylesheet must return 200 and `text/css` from the API's
`/site/archives/reader.css` path. Frontend bundles are not hosted at the API's
`/assets/` path and the standalone reader never requests them. The article HTML
remains no-store; correctly versioned stylesheet requests are publicly cached.

Purge old CDN/LiteSpeed detail-page responses after installing these rules.
Previously issued 301/308 redirects may also remain in a browser cache; use a
fresh browser session to distinguish those from the current server response.
If OpenLiteSpeed is used, reload rewrite configuration through DirectAdmin's
normal file-save/reload workflow; ZIP extraction alone may not reload it. See
[DirectAdmin's guidance](https://docs.directadmin.com/webservices/openlitespeed/index.html#how-to-make-ols-automatically-reload-after-htaccess-changes).
Verify that the hosting server supports the header directives before calling
the deployment complete. Local rule regression tests model the configured
conditions; they do not run the production webserver.

## Trusted media origins

Defaults are `SEO_MEDIA_ORIGIN=https://api.organicemperor.com` on Django and
`VITE_PUBLIC_MEDIA_ORIGIN=https://api.organicemperor.com` at frontend build time.
Relative image paths resolve against that public HTTPS origin. If media moves
to a CDN, set both to the same HTTPS origin and rebuild. Additional trusted
HTTPS origins may be configured as comma-separated `SEO_IMAGE_ORIGINS` and
`VITE_PUBLIC_IMAGE_ORIGINS`, with matching values. Include only origins serving
public images; schemes, credentials and untrusted origins are rejected.
Canonical site origins are fixed to the two requested public domains and are
never taken from request Host or client content. Product gallery changes do
not change sharing images.

## Sharing image dimensions

Both `og:image` and `twitter:image` point to a real **1200 × 630 PNG**. The
`og:image:width`, `og:image:height`, and `og:image:type` tags declare that file's
actual dimensions and MIME type. These are pixel dimensions, not CSS sizing
instructions; putting wide dimensions on the original portrait emblem would
not prevent a platform from cropping it.

Django serves the full source image, proportionally contained within a wide
canvas with 48-pixel padding. Archives covers and their brand fallback use the
night-mode green `#101a16`; product images retain a white background. The
Archives article image URL includes `frame=101a16` in both server and browser
metadata to identify the changed padding for social caches. This parameter
does not allow visitors to choose a background or source file. Original reader
and gallery images are unchanged. The public image endpoints are:

```text
/site/storefront/share-image.png
/site/archives/share-image.png
/site/storefront/products/<slug>/share-image.png
/site/archives/posts/<slug>/share-image.png
```

These endpoints open only the stored model image or a fixed packaged brand
asset, and accept no remote source URL or custom dimensions. They enforce
public visibility on every request, including staff requests and old versioned
URLs. Missing, corrupt or oversized source files use the brand fallback. Image
responses carry no-store so a withdrawal takes effect at the origin. The
version query changes when a different uploaded source is selected; social
platforms may still cache previously fetched previews.

Deploy the backend image endpoints before installing the new frontend heads,
then verify the actual image URL returns `image/png` at 1200 × 630. The new
fallback URLs also work for static listing heads. Product/article titles and
images still require the public-domain HTML proxy described above. Refresh a
platform preview after verifying the deployed HTML and image; existing posts
may retain the old crop.

## Verify before calling production complete

Run unauthenticated requests against **the public frontend URLs**, not just
the API endpoints, and inspect the response without JavaScript:

```powershell
curl.exe -sS -D product-headers.txt https://organicemperor.com/products/ACTUAL-SLUG -o product.html
curl.exe -sS -D article-headers.txt https://organicarchives.organicemperor.com/posts/ACTUAL-SLUG -o article.html
Select-String -Path product.html,article.html -Pattern '<title>|canonical|og:|twitter:|article:'
```

Expect one entry per field, the actual primary/cover image, absolute HTTPS URLs,
and correct site names. Request the `og:image` URL with `curl.exe -D - -o NUL`
without cookies: it must return 200 and an image content type. Confirm no
authentication, crawler block, or private storage dependency. Check missing,
inactive, draft, undated and scheduled content returns 404 without private
text. View Source should show the same head; browser Inspector alone is not
proof. Compare regular and crawler requests (for example `curl.exe -A
facebookexternalhit/1.1 …`) to confirm the same content.

Also navigate between two products, between two articles, back to each listing,
and through browser Back/Forward. Titles, canonical URLs, descriptions, images,
and article-only fields must update; gallery selection must retain the primary
sharing image. Existing accounts, carts, checkout and publisher previews should
still work. Static listing heads retain the appropriate brand image, including
`https://api.organicemperor.com/site/archives/share-image.png`.

For article crawling, raw API HTML must also include `<div id="app"><article>`
and the actual body text. Confirm it contains one styled article and no Vue
module script; canonical frontend links still open the interactive Vue reader.
Fetch the public Archives `/sitemap.xml`
and `/robots.txt`: expect XML and plain text respectively, rather than the SPA
shell. Verify the sitemap lists public canonical post URLs, excludes unpublished
content and removes a withdrawn post. The robots file must advertise the public
Archives sitemap URL. Submit that URL in Search Console after deployment.

After verifying origin HTML and purging any hosting page cache, request a fresh
preview in [Meta Sharing Debugger](https://developers.facebook.com/tools/debug/)
(enter the canonical URL, then **Scrape Again**) and
[LinkedIn Post Inspector](https://www.linkedin.com/post-inspector/).
[LinkedIn's instructions](https://www.linkedin.com/help/linkedin/answer/a6269011)
explain refreshing cached previews. Recheck the fetched image and scrape time;
platform caches can outlive a site deployment. Existing published social posts
may retain their original preview. Do not add arbitrary query strings to the
canonical URL as a cache workaround.

Repository validation covers Django raw HTML, visibility, public local media,
safe values, browser route changes and packaging consistency. Production crawler routing, public asset access and actual platform recrawls require the above
deployment verification; they have not been performed by editing this repo.
