# OrganicArchives public article routing

Please check the active HTTPS virtual host and document root for
`organicarchives.organicemperor.com`. The deployed Django HTML renderer works,
but the public frontend request currently returns its static Vue index.

Verified on October 2, 2026 with unauthenticated HTTPS requests:

| Request | Observed result | Required result |
| --- | --- | --- |
| `/posts/male-cats-a-urinary-diet` on the Archives domain | 200, site title and OA emblem | 200, article title and cover from Django |
| `/posts/male-cats-a-urinary-diet/` on the Archives domain | 200, same static index | 308 to the non-slash Archives URL |
| A nonexistent `/posts/<slug>` on the Archives domain | 200, same static index | 404 |
| `https://api.organicemperor.com/site/archives/posts/male-cats-a-urinary-diet` | 200, correct article metadata | Already correct |

The correct public cover is accessible without authentication at
`https://api.organicemperor.com/media/archives/covers/2026/10/Cover.png` (200,
`image/png`). The frontend HTML currently identifies the page as `website`, has
the homepage canonical URL, and matches the built static index byte for byte.

The supplied `.htaccess` contains the detail proxy before the SPA catch-all.
Its independent 308 rule is also not affecting requests, so please first:

1. Confirm the actual **HTTPS** document root and active `.htaccess`; check any
   separate `private_html` root or aliases. The account owner reports the file
   is in `/domains/organicarchives.organicemperor.com/public_html`; this folder
   alone does not confirm the HTTPS document root.
2. Inspect parent-directory and virtual-host rewrites for an earlier rewrite to
   `index.html`, and confirm that the intended rewrite configuration is loaded.
3. Confirm the webserver edition. If it is **OpenLiteSpeed**, reload its rewrite
   configuration after archive extraction: it reads `.htaccess` at startup.
   DirectAdmin can trigger a reload when the file is saved in File Manager, but
   extraction may leave the previously loaded rules active. See
   [DirectAdmin's OpenLiteSpeed reload guidance](https://docs.directadmin.com/webservices/openlitespeed/index.html#how-to-make-ols-automatically-reload-after-htaccess-changes).
4. Once requests reach the rules, configure LiteSpeed's fixed HTTPS API proxy
   target as required by the host. See the
   [official LiteSpeed proxy instructions](https://docs.litespeedtech.com/lsws/cp/cpanel/rewrite-proxy/).

Required mapping for all visitors and crawlers, before SPA fallback:

```text
https://organicarchives.organicemperor.com/posts/<slug>
    -> https://api.organicemperor.com/site/archives/posts/<slug>
```

Preserve the upstream body, status and no-store headers. Keep the public URL in
the browser, validate upstream TLS, and leave assets, APIs, admin and security
headers in place. Please do not redirect visitors to the API domain or return
the static index on upstream 404s. After configuration, verify the three frontend
responses above, then request a fresh LinkedIn preview of the canonical URL.
