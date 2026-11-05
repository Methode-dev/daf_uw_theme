# -*- coding: utf-8 -*-
"""The Méthode palette is restated in three independent places.

``models/res_company.py`` (field defaults), ``models/ir_http.py`` (session_info
fallbacks) and ``views/web_assets.xml`` (the server-rendered ``:root`` block)
each carry their own copy.  ir_http imports the constants so it cannot drift,
but the XML holds string literals — and it drifting out of sync is exactly the
failure that left the backend rendering Aura's grey after the palette changed.

These tests are cheap and pin that agreement.
"""

import os
import re

from odoo.tests.common import TransactionCase

from odoo.addons.aura_backend_theme.models.res_company import (
    DEFAULT_BRAND,
    DEFAULT_BRAND_DARK,
    METHODE_BG_PRIMARY,
    METHODE_CARD_BG,
    METHODE_SECONDARY,
    METHODE_TOPBAR_BG,
    METHODE_TOPBAR_TEXT,
)

WEB_ASSETS_XML = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'views', 'web_assets.xml',
)

# field name -> the constant its XML fallback must restate
XML_FALLBACKS = {
    'tbt_brand_color': DEFAULT_BRAND,
    'tbt_topbar_bg': METHODE_TOPBAR_BG,
    'tbt_topbar_text': METHODE_TOPBAR_TEXT,
    'tbt_content_bg': METHODE_BG_PRIMARY,
    'tbt_card_bg': METHODE_CARD_BG,
}


class TestThemeDefaults(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with open(WEB_ASSETS_XML, encoding='utf-8') as fh:
            cls.web_assets_source = fh.read()

    def test_xml_fallbacks_match_python_constants(self):
        """web_assets.xml restates the same palette as res_company.py."""
        for fname, expected in XML_FALLBACKS.items():
            occurrences = self.web_assets_source.count(
                "tbt_company.%s or '%s'" % (fname, expected)
            )
            # Twice: once in the backend template, once in the frontend one.
            self.assertEqual(
                occurrences, 2,
                "web_assets.xml should fall back to %s for %s in both the "
                "backend and frontend templates, found %s occurrence(s). "
                "The palette has drifted between res_company.py and the XML."
                % (expected, fname, occurrences),
            )

    def test_no_aura_palette_left_in_xml(self):
        """Aura's old defaults are gone from the fields we migrated.

        Scoped to those fields on purpose.  The `tbt_sidebar_*` fallbacks still
        hold Aura greys (#f1f2f4, #555b70, …) and that is deliberate: the
        sidebar was deleted in §3.1, nothing consumes `--tbt-sidebar-*`, and
        rewriting dead values would be scope creep.  Revisit if a sidebar ever
        returns.
        """
        stale_by_field = {
            # '#FAA140' was a short-lived orange primary, '#000000' the black
            # primary of the warm palette superseded in 19.0.1.7.0.
            'tbt_brand_color': ('#242424', '#FAA140', '#000000'),
            'tbt_brand_color_rgb': ('36,36,36', '250,161,64', '0,0,0'),
            # '#E9DBCA' = the short-lived warm navbar, before it became clear
            # Odoo's stock bar renders black from $o-brand-odoo regardless.
            'tbt_topbar_bg': ('#ffffff', '#E9DBCA'),
            # Black topbar text was unreadable once the bar itself went black.
            'tbt_topbar_text': ('#0c0f0f', '#000000'),
            'tbt_content_bg': ('#f6f6f6', '#FDFAF6'),
            'tbt_card_bg': ('#F2F2F2',),
        }
        for fname, stale_values in stale_by_field.items():
            for stale in stale_values:
                self.assertNotIn(
                    "tbt_company.%s or '%s'" % (fname, stale),
                    self.web_assets_source,
                    "Superseded default %s is still the fallback for %s in "
                    "web_assets.xml" % (stale, fname),
                )

    def test_secondary_is_not_the_brand_primary(self):
        """The secondary (#F04F47) must never drive --bs-primary.

        Primary is the palette blue; the secondary is applied per-component for
        emphasis. Wiring it into the brand colour would tint every button, link
        and focus ring in the backend coral — next to a red danger colour.
        """
        self.assertNotEqual(DEFAULT_BRAND, METHODE_SECONDARY)
        company = self.env['res.company'].create({'name': 'Accent Probe'})
        self.assertEqual(company.tbt_brand_color, DEFAULT_BRAND)
        self.assertEqual(company.tbt_brand_color_dark, DEFAULT_BRAND_DARK)

    def test_web_assets_template_is_installed(self):
        """The :root block and the FA6 <link> tags actually load.

        fa_v6_shim.scss rewrites every `.fa` to the FA6 webfont; if this
        template is not in the manifest's `data`, that font is never fetched
        and every icon in the backend renders as a blank box.
        """
        template = self.env.ref(
            'aura_backend_theme.tbt_web_fonts_backend', raise_if_not_found=False,
        )
        self.assertTrue(
            template,
            "views/web_assets.xml is missing from the manifest's data list",
        )

    def test_brand_dark_fallback_matches_computed_value(self):
        """The hardcoded brand-dark literal in the XML matches _darken_hex()."""
        company = self.env['res.company'].create({'name': 'Palette Probe'})
        self.assertEqual(company.tbt_brand_color, DEFAULT_BRAND)
        literals = re.findall(
            r"tbt_company\.tbt_brand_color_dark or '(#[0-9A-Fa-f]{6})'",
            self.web_assets_source,
        )
        self.assertTrue(literals, "no brand-dark fallback found in web_assets.xml")
        for literal in literals:
            self.assertEqual(
                literal.upper(), company.tbt_brand_color_dark.upper(),
                "web_assets.xml hardcodes a brand-dark value that no longer "
                "matches what _darken_hex() derives from %s" % DEFAULT_BRAND,
            )
