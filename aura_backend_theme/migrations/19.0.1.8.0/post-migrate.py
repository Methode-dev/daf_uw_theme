# -*- coding: utf-8 -*-
"""Move the stored brand colour to the DAF Under Writing logo blue (2026-11).

Primary goes from the owner blue ``#0A8FDC`` (dark ``#07649A``) to the
logo's ``#0E58F0`` (dark ``#093DA8``, derived by _compute_tbt_brand_palette).

As in 19.0.1.4.0 and 19.0.1.7.0, this has to be a stored-value migration and
not only a ``default=`` change: ``theme_bootstrap.js`` and
``views/web_assets.xml`` write these company values as inline custom
properties on ``<html>``, which beat every stylesheet rule.  A row still
holding the old blue would keep it no matter what the SCSS says.

Each field lists every earlier default it may overwrite (including the values
19.0.1.7.0 superseded, so a database that skipped it heals too).  Anything
else was chosen deliberately by an administrator and is left alone, which also
keeps the script idempotent.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

NEW_BRAND = '#0E58F0'

# field -> (values this migration may overwrite, new default)
PALETTE_MIGRATION = {
    'tbt_brand_color': (('#0A8FDC', '#000000', '#242424', '#FAA140'), NEW_BRAND),
    'tbt_dashboard_card_3_color': (('#0A8FDC', '#FAA140', '#F59E0B'), NEW_BRAND),
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

    # tbt_brand_color_dark / _rgb are stored computes of the brand colour.
    companies._compute_tbt_brand_palette()
    companies.flush_recordset()

    _logger.info(
        "DAF Under Writing logo blue seeded on %s/%s companies "
        "(customised colours preserved)", migrated, len(companies),
    )
