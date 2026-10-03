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

Archives article responses also contain the title, complete excerpt, byline,
cover and ordered body sections inside `#app` before JavaScript runs. Vue replaces
this content on mount. The fallback uses a conservative Markdown subset for
headings, lists, quotes and paragraphs; inline Markdown links/emphasis become
plain words. Heading and quote blocks stay literal text, as in the reader.
All text is escaped, uploaded media uses the trusted HTTPS origins below, and
embedded videos become links to validated YouTube/Vimeo players. No remote
content is fetched by Django. A missing or duplicate article mount returns 503.
This follows [Google's guidance on serving content in the initial HTML](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics).

Archives also serves a dynamic `/sitemap.xml` and `/robots.txt`. The sitemap lists
the canonical homepage and public posts only, with publication/update dates;
drafts, undated and scheduled posts are excluded even for staff. Both endpoints
accept GET/HEAD and use no-store so withdrawals take effect immediately.

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
   Show hidden files in the hosting file manager and explicitly overwrite the
   existing `.htaccess`; extracting only newer files can leave an older rule in
   place. Frontend ZIPs now give `.htaccess` the same fresh timestamp as the entry
   document, rather than the fixed timestamp used for immutable assets.
   An atomic release switch is preferable where the host supports it.
5. Bypass/purge any CDN or LiteSpeed full-page cache for `/products/*`, `/posts/*`,
   `/sitemap.xml`, `/robots.txt` and `/site/*`. Keep hashed asset caching. Dynamic responses carry
   `Cache-Control: no-cache, no-store, must-revalidate` so edits and withdrawals
   take effect immediately. Check that the host respects this header and 404s.

## Required public-domain routing

The packaged `.htaccess` has fixed upstream proxy rules before SPA fallback:

| Public domain and path | Django upstream |
| --- | --- |
| `organicemperor.com/products/<slug>` | `https://api.organicemperor.com/site/storefront/products/<slug>` |
| `organicarchives.organicemperor.com/posts/<slug>` | `https://api.organicemperor.com/site/archives/posts/<slug>` |
| `organicarchives.organicemperor.com/sitemap.xml` | `https://api.organicemperor.com/site/archives/sitemap.xml` |
| `organicarchives.organicemperor.com/robots.txt` | `https://api.organicemperor.com/site/archives/robots.txt` |

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

On LiteSpeed/DirectAdmin, ask the host to configure a **Web Server external
application** for the fixed HTTPS API upstream. LiteSpeed does not automatically
create a proxy target for a domain name, even if it is hosted on the same server.
The provider must configure the backend address, HTTPS connection and API Host
header, then enable the two path mappings. See
[LiteSpeed proxy setup](https://docs.litespeedtech.com/lsws/cp/cpanel/rewrite-proxy/).
Apache's `SSLProxyEngine` instruction alone does not establish this LiteSpeed
external application. If `[P]` is unavailable in the hosting plan, configure
the **same two mappings** through the host's reverse proxy/vhost facility before
the static SPA fallback, preserving 404 and no-store. Do not replace `[P]` with
a redirect to the API domain. The exact host facility depends on whether it
runs Apache, LiteSpeed Enterprise, or OpenLiteSpeed; this repository cannot
configure that account-level capability. A public URL returning the old static
head means routing is incomplete. A 500/503 indicates proxy/build configuration
needs fixing. Browser-only head updates do not complete deployment.

If the frontend returns the emblem but Django returns the article's cover,
compare the active `.htaccess` in the Archives document root with
`frontend/public/.htaccess`. The `^posts/` proxy must appear **before** the
`RewriteRule ^ index.html [L]` catch-all. The active file should contain:

```apache
RewriteCond %{HTTP_HOST} ^organicarchives\.organicemperor\.com$ [NC]
RewriteRule ^posts/([A-Za-z0-9_-]+)$ https://api.organicemperor.com/site/archives/posts/$1 [P,L]
```

If that rule is present yet the frontend still serves the static document,
check parent-directory or vhost rewrite rules that run earlier, the actual
subdomain document root, and LiteSpeed's rewrite configuration/logs. If it
returns 500 after the rule is installed, ask the host to check the fixed proxy
external application. Keep TLS verification enabled. A browser redirect or
JavaScript metadata update does not replace this server routing.

To distinguish rules that are not taking effect from a proxy-target problem,
request a valid detail URL with a trailing slash **without following redirects**:

```powershell
curl.exe -sS -D - -o NUL https://organicarchives.organicemperor.com/posts/male-cats-a-urinary-diet/
```

This file's explicit rule should return 308 with the non-slash frontend URL in
`Location`. If it instead returns the static index with 200, check the active
HTTPS document root (including any separate `private_html` root), that root's
`.htaccess`, and earlier parent/vhost rewrites before diagnosing the proxy.
The file contents alone do not prove that the request reaches that file.

If the host uses **OpenLiteSpeed**, it must reload the rewrite configuration
after `.htaccess` changes. DirectAdmin normally triggers this when the file is
saved in File Manager; do not assume ZIP extraction also reloads it. This
requirement differs from LiteSpeed Enterprise. See
[DirectAdmin's OpenLiteSpeed guidance](https://docs.directadmin.com/webservices/openlitespeed/index.html#how-to-make-ols-automatically-reload-after-htaccess-changes).

See [hosting handoff with observed response details](SEO_HOSTING_HANDOFF.md).

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
canvas with 48-pixel padding. Product images and article covers use a white
background; the brand fallbacks use their brand backgrounds. Original reader
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

For article crawling, raw HTML must also include `<div id="app"><article>` and
the actual body text before JavaScript. Confirm it contains one article and that
Vue replaces the fallback normally. Fetch the public Archives `/sitemap.xml`
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
safe values, browser route changes and packaging consistency. Production proxy
support, public asset access and actual platform recrawls require the above
deployment verification; they have not been performed by editing this repo.
