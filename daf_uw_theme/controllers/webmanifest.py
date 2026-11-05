from odoo.addons.web.controllers.webmanifest import WebManifest


class WebManifestBrand(WebManifest):
    """Méthode icons in the PWA manifest.

    /web/manifest.webmanifest is generated in Python, not QWeb (see
    web/controllers/webmanifest.py), so it is the one icon surface
    views/favicon_templates.xml cannot reach.  Without this override an
    "Add to Home Screen" from the backend installs with Odoo's own purple
    icon while every browser tab shows the Méthode mark.

    ⚠ ONLY `icons` IS TOUCHED.  Stock also sets name (from the
    web.web_app_name config parameter), background_color and theme_color to
    Odoo's #714B67 — those are the splash screen and the mobile chrome, not
    the icon, and are left to whoever owns that decision.  The brand value
    for them would be $m-bg-primary / #F4F7FE (static/src/scss/
    brand_variables.scss); the matching `<meta name="theme-color">` lives in
    web.webclient_bootstrap.
    """

    def _get_webmanifest(self):
        manifest = super()._get_webmanifest()
        # Same two sizes stock advertises, so nothing downstream has to cope
        # with a size disappearing; only the files change.
        manifest['icons'] = [{
            'src': '/daf_uw_theme/static/src/img/favicon/android-chrome-%s.png' % size,
            'sizes': size,
            'type': 'image/png',
        } for size in ('192x192', '512x512')]
        return manifest
