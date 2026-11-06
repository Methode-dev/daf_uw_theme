# -*- coding: utf-8 -*-
"""Move the card / form-sheet surface from white to the measured brand grey.

THEME_PLAN §14 open question 3, resolved in P5: `03-card.png` was measured and
its surface is ``#F2F2F2``, not white.  White had been the interim default; the
owner rejected it on sight, because a white sheet sitting on the warm ``#FDFAF6``
page reads as an unfinished gap rather than as a surface.

This has to be a stored-value migration rather than only a ``default=`` change,
for the reason spelled out in 19.0.1.4.0: ``theme_bootstrap.js`` writes these
company values as inline styles on ``<html>``, and inline custom properties beat
every stylesheet rule.  A row still holding ``#FFFFFF`` would keep white sheets
no matter what the SCSS says, with no error to explain why.

Kept separate from the 19.0.1.4.0 script rather than folded into it: databases
that already ran that version would never re-run it, so the change would reach
new installs only.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Values this migration is allowed to overwrite -> the new default.
# '#ffffff' is both Aura's original and the interim Méthode value, so a single
# entry covers every database that predates the measurement.  Anything else was
# set deliberately in the Theme Settings dialog and is left alone, which also
# makes this script idempotent.
SUPERSEDED = ('#ffffff',)
NEW_CARD_BG = '#F2F2F2'


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    companies = env['res.company'].sudo().search([])
    if not companies:
        return

    migrated = 0
    for company in companies:
        current = (company.tbt_card_bg or '').strip()
        # Empty rows take the new value too: they would otherwise fall through
        # to the hardcoded fallbacks in ir_http.py and views/web_assets.xml.
        if not current or current.lower() in SUPERSEDED:
            if current != NEW_CARD_BG:
                company.tbt_card_bg = NEW_CARD_BG
                migrated += 1

    _logger.info(
        "Card surface moved to %s on %s/%s companies (customised values kept)",
        NEW_CARD_BG, migrated, len(companies),
    )
