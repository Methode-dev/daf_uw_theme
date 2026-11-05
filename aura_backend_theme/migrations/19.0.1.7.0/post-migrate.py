# -*- coding: utf-8 -*-
"""Move the stored palette to the owner's blue palette (2026-11).

The theme was re-coloured to match the React front end: page ``#F4F7FE``,
card ``#FFFFFF``, primary ``#0A8FDC`` (dark ``#07649A``), text ``#111827``.

As in 19.0.1.4.0, this has to be a stored-value migration and not only a
``default=`` change: ``theme_bootstrap.js`` and ``views/web_assets.xml`` write
these company values as inline custom properties on ``<html>``, which beat
every stylesheet rule.  A row still holding the old warm palette would keep it
no matter what the SCSS says.

Each field lists every earlier default it may overwrite (the Méthode warm
palette plus the Aura values the earlier scripts superseded, so a database
that skipped them heals too).  Anything else was chosen deliberately and is
left alone, which also keeps the script idempotent.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# field -> (values this migration may overwrite, new default)
PALETTE_MIGRATION = {
    'tbt_brand_color': (('#000000', '#242424', '#FAA140'), '#0A8FDC'),
    'tbt_content_bg': (('#FDFAF6', '#f6f6f6'), '#F4F7FE'),
    'tbt_card_bg': (('#F2F2F2', '#ffffff'), '#FFFFFF'),
    'tbt_dashboard_card_1_color': (('#000000', '#2F6BFF'), '#111827'),
    'tbt_dashboard_card_2_color': (('#6D6D6D', '#EF4444'), '#6B7280'),
    'tbt_dashboard_card_3_color': (('#FAA140', '#F59E0B'), '#0A8FDC'),
    'tbt_dashboard_card_4_color': (('#E9DBCA', '#22C55E'), '#E3E9F6'),
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
            if not current or current.lower() in [v.lower() for v in superseded]:
                if current != new_default:
                    values[fname] = new_default
        if values:
            company.write(values)
            migrated += 1

    # The brand-dark factor changed too (0.55 -> 0.70), so recompute every
    # company, not only the ones whose brand colour was rewritten.
    companies._compute_tbt_brand_palette()
    companies.flush_recordset()

    _logger.info(
        "Blue palette seeded on %s/%s companies (customised colours preserved)",
        migrated, len(companies),
    )
