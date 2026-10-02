# Product and article sharing metadata

Public paths remain `/products/<slug>` and `/posts/<slug>` (Vue history routing).
There are no fragment-based detail URLs to migrate. Listing anchors such as
`/#catalog` still work. No share buttons existed that needed changing.

Both applications update the head during navigation, including back/forward.
Django additionally returns the **built Vue HTML shell** with an escaped head
at `/site/storefront/products/<slug>` and `/site/archives/posts/<slug>`. This is
used for every visitor through the public-domain reverse proxy, with no bot
detection, external fetches, or metadata cache. Product visibility and scheduled
article publication use the same filters as the public APIs. Missing/private
content returns HTTP 404, even for authenticated staff. Missing build shells
return 503 for otherwise-public content, rather than misleading generic HTML.

## Build and deploy one matching release

From the repository root (Windows):

```powershell
.\.org_env\Scripts\python.exe scripts/package_frontends.py
.\.org_env\Scripts\python.exe scripts/package_backend.py
```

The first command always typechecks and builds both sites, validates assets,
creates `dist.zip` / `dist-archives.zip`, and writes generated HTML to
`backend/site_shells/`. The second includes only those two validated generated
shells in `backend.zip`, and fails if they do not match the builds. Deploy all
three archives as one release. No database migrations or new dependencies are
required. Do not edit the generated shells or hard-code bundle hashes.

1. Upload the frontend assets to both existing document roots, retaining old
   hashed assets while the release rolls out. Keep the current index documents
   and rewrite rules until the backend is ready.
2. Extract `backend.zip` into the existing Django deployment. Confirm
   `backend/site_shells/storefront.html` and `archives.html` exist, then restart
   Passenger using the hosting panel's existing restart action.
3. Verify the two Django HTML endpoints at `https://api.organicemperor.com/site/…`
   with actual public slugs. They must return 200, `text/html`, the correct head,
   and the same `/assets/…` references as the frontend release.
4. Install the updated frontend `index.html` and `.htaccess` files. Enable the
   HTTPS proxy configuration below **before** exposing the new rewrite rules.
   An atomic release switch is preferable where the host supports it.
5. Bypass/purge any CDN or LiteSpeed full-page cache for `/products/*`, `/posts/*`
   and `/site/*`. Keep hashed asset caching. Dynamic responses carry
   `Cache-Control: no-cache, no-store, must-revalidate` so edits and withdrawals
   take effect immediately. Check that the host respects this header and 404s.

## Required public-domain routing

The packaged `.htaccess` has fixed upstream proxy rules before SPA fallback:

| Public domain and path | Django upstream |
| --- | --- |
| `organicemperor.com/products/<slug>` | `https://api.organicemperor.com/site/storefront/products/<slug>` |
| `organicarchives.organicemperor.com/posts/<slug>` | `https://api.organicemperor.com/site/archives/posts/<slug>` |

Trailing slash detail URLs redirect to their canonical non-slash URL. Query
strings do not change metadata. Responses must preserve the upstream status,
content type, cache headers and body. Route these paths for **all** user agents;
never serve `index.html` on a missing/private detail page. `/assets/*`, `/media/*`,
existing APIs, admin, account and checkout routing remain as before.

For Apache, the host must enable `mod_rewrite`, `mod_proxy`, `mod_proxy_http`,
`mod_ssl`, and the existing `.htaccess` permissions. In both HTTPS frontend
virtual hosts, set the following via DirectAdmin's supported custom vhost
configuration (these directives cannot be set in `.htaccess`):

```apache
ProxyRequests Off
SSLProxyEngine On
SSLProxyVerify require
SSLProxyCheckPeerName On
# Point SSLProxyCACertificateFile at the host's actual trusted CA bundle.
# Debian/Ubuntu example:
SSLProxyCACertificateFile /etc/ssl/certs/ca-certificates.crt
```

Validate the generated webserver configuration before reload. The API's TLS
certificate must validate. See [Apache proxy documentation](https://httpd.apache.org/docs/2.4/mod/mod_proxy.html)
and [HTTPS proxy directives](https://httpd.apache.org/docs/2.4/mod/mod_ssl.html#sslproxyengine).

On LiteSpeed/DirectAdmin, ask the host to enable HTTPS proxy rewrite support for
the fixed API upstream. If `[P]` is unavailable in the hosting plan, configure
the **same two mappings** through the host's reverse proxy/vhost facility before
the static SPA fallback, preserving 404 and no-store. Do not replace `[P]` with
a redirect to the API domain. The exact host facility depends on whether it
runs Apache, LiteSpeed Enterprise, or OpenLiteSpeed; this repository cannot
configure that account-level capability. A public URL returning the old static
head means routing is incomplete. A 500/503 indicates proxy/build configuration
needs fixing. Browser-only head updates do not complete deployment.

## Trusted media origins

Defaults are `SEO_MEDIA_ORIGIN=https://api.organicemperor.com` on Django and
`VITE_PUBLIC_MEDIA_ORIGIN=https://api.organicemperor.com` at frontend build time.
Relative image paths resolve against that public HTTPS origin. If media moves
to a CDN, set both to the same HTTPS origin and rebuild. Additional trusted
HTTPS origins may be configured as comma-separated `SEO_IMAGE_ORIGINS` and
`VITE_PUBLIC_IMAGE_ORIGINS`, with matching values. Include only origins serving
public images; schemes, credentials and untrusted origins are rejected.
Canonical site origins are fixed to the two requested public domains and are
never taken from request Host or client content. No dimensions/MIME tags are
invented. Product gallery changes do not change sharing images.

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
`https://organicarchives.organicemperor.com/OA-Emblem-BBG.png`.

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
safe values, browser route changes and packaging consistency. Production proxy
support, public asset access and actual platform recrawls require the above
deployment verification; they have not been performed by editing this repo.
