# -*- coding: utf-8 -*-
"""Seed the Méthode palette onto companies that predate it (THEME_PLAN §9.2).

Changing ``default=`` on a field only affects rows created afterwards, so
without this every existing company keeps Aura's slate/grey palette.  Because
``theme_bootstrap.js`` writes those stored values as inline styles on
``<html>``, and inline custom properties beat every stylesheet rule, a stale
row silently defeats the whole brand with no error to explain why.

Each field lists *every* value it is allowed to overwrite: Aura's original
default plus any interim Méthode default since superseded.  Two of those
interim values were live only briefly:

  * ``tbt_brand_color`` defaulted to the orange accent before the brand assets
    were re-read and primary settled on black.
  * ``tbt_topbar_bg`` defaulted to the warm raised-surface token before it
    became clear that Odoo's stock navbar takes its background from
    ``$o-brand-odoo`` and renders black regardless.

Listing them here means a database that caught either window heals instead of
keeping a value the UI never honoured.  Anything outside these lists was set
deliberately and is left alone, which also keeps the script idempotent.

This supersedes the 19.0.1.2.0 script: it covers the same ground plus the
topbar, so a database at any earlier version reaches the same end state.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# field -> (values this migration may overwrite, new default)
PALETTE_MIGRATION = {
    # '#242424' = Aura slate; '#FAA140' = the short-lived orange primary.
    'tbt_brand_color': (('#242424', '#FAA140'), '#000000'),
    # '#ffffff' = Aura; '#E9DBCA' = the short-lived warm navbar.
    'tbt_topbar_bg': (('#ffffff', '#E9DBCA'), '#000000'),
    # '#0c0f0f' = Aura; '#000000' = black text, unreadable on a black bar.
    'tbt_topbar_text': (('#0c0f0f', '#000000'), '#FFFFFF'),
    'tbt_content_bg': (('#f6f6f6',), '#FDFAF6'),
    'tbt_card_bg': (('#ffffff',), '#FFFFFF'),
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].sudo().search([])
    if not companies:
        return

    migrated = 0
    for company in companies:
        values = {}
        for fname, (superseded, new_default) in PALETTE_MIGRATION.items():
            current = (company[fname] or '').strip()
            # NULL/empty rows take the new default too: they would otherwise
            # fall through to the hardcoded fallbacks in ir_http.py.
            if not current or current.lower() in [v.lower() for v in superseded]:
                if current != new_default:
                    values[fname] = new_default
        if values:
            company.write(values)
            migrated += 1

    # tbt_brand_color feeds a stored compute (brand_rgb, brand_dark, the whole
    # sidebar ramp).  write() triggers it, but companies whose brand colour was
    # customised never got written above and may still hold a NULL ramp from an
    # install that predated the field.
    companies._compute_tbt_brand_palette()
    companies.flush_recordset()

    _logger.info(
        "Méthode palette seeded on %s/%s companies (customised colours preserved)",
        migrated, len(companies),
    )
