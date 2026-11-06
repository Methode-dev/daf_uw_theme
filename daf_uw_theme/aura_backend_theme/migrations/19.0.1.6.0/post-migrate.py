# -*- coding: utf-8 -*-
"""Re-seed the four dashboard card colours onto the brand (THEME_PLAN §13.2/§13.8).

Aura shipped ``#2F6BFF`` blue, ``#EF4444`` red, ``#F59E0B`` amber and
``#22C55E`` green.  The Méthode brand is monochrome plus a single orange accent,
and §13.2 is explicit that those seven-hue habits must not be carried into it, so
P8's dashboard takes its emphasis from the size of a figure rather than from the
colour of a tile.

Changing ``default=`` only affects rows created afterwards, so without this every
existing company keeps Aura's palette in the Theme Settings colour pickers.

⚠ NOTHING CONSUMES THESE VALUES TODAY.  The ``--tbt-dashboard-card-*`` custom
properties are injected on every page load — twice, backend and frontend, see
``views/web_assets.xml`` — and read by no stylesheet, because the Aura dashboard
SCSS that used them was deleted in §3.1/§3.4.  This migration therefore changes
nothing visible; it exists so that the stored state matches the brand rather than
lying in wait for whatever reads it next, and so an administrator opening the
pickers is not offered four hues the design forbids.

Only Aura's exact defaults are overwritten.  A colour anyone chose deliberately
is left alone, which also makes the script idempotent.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# field -> (values this migration may overwrite, new default)
CARD_MIGRATION = {
    'tbt_dashboard_card_1_color': (('#2F6BFF',), '#000000'),   # ink
    'tbt_dashboard_card_2_color': (('#EF4444',), '#6D6D6D'),   # secondary ink
    'tbt_dashboard_card_3_color': (('#F59E0B',), '#FAA140'),   # the one accent
    'tbt_dashboard_card_4_color': (('#22C55E',), '#E9DBCA'),   # warm surface
}


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].sudo().search([])
    if not companies:
        return

    migrated = 0
    for company in companies:
        values = {}
        for fname, (superseded, new_default) in CARD_MIGRATION.items():
            current = (company[fname] or '').strip()
            # Empty rows take the new default too: they would otherwise fall
            # through to the hardcoded fallbacks in ir_http.py and web_assets.xml.
            if not current or current.lower() in [v.lower() for v in superseded]:
                if current != new_default:
                    values[fname] = new_default
        if values:
            company.write(values)
            migrated += 1

    _logger.info(
        "Dashboard card colours re-seeded on %s/%s companies "
        "(deliberate choices preserved)",
        migrated, len(companies),
    )
