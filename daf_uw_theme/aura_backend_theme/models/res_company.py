# -*- coding: utf-8 -*-

import re

from odoo import api, fields, models
from odoo.exceptions import ValidationError


HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")

# Méthode brand palette (THEME_PLAN §5.1).  These defaults are what
# theme_bootstrap.js writes as inline styles on <html>, which beat every
# stylesheet rule at the same custom-property name (§9.2) — so the brand has
# to be seeded *here*, not fought with !important in daf_uw_theme's SCSS.
#
# Keep in lockstep with the fallbacks in models/ir_http.py and
# views/web_assets.xml; all three restate these values independently.
# DAF Under Writing palette, 2026-11 (from the client's logo).  Brand/primary
# is the logo blue; its dark variant is what _compute_tbt_brand_palette derives
# (factor 0.70 lands exactly on #093DA8).
DEFAULT_BRAND = "#0E58F0"           # $m-primary — drives --bs-primary, focus
DEFAULT_BRAND_DARK = "#093DA8"      # $m-primary-dark — hover, links
METHODE_ACCENT = DEFAULT_BRAND      # $m-accent is the primary since 2026-11
METHODE_SECONDARY = "#6D3BFF"       # $m-secondary — emphasis fills (violet)
METHODE_BG_PRIMARY = "#F4F7FE"      # $m-bg-primary — page / app background
METHODE_BG_SECONDARY = "#E3E9F6"    # $m-bg-secondary — raised surfaces, group
                                    # headers, hovers. Not the navbar: see below.
METHODE_TEXT = "#111827"            # $m-text
METHODE_TEXT_SECONDARY = "#6B7280"  # $m-text-secondary
# The navbar renders as a black plate, matching 02-display-title.png.  That is
# not a free choice: Odoo's stock navbar takes its background from
# $o-brand-odoo, which brand_variables.scss sets to $m-text.  These fields
# record the value the UI actually produces — a stored setting that disagrees
# with what renders is a bug, and nothing has consumed tbt_topbar_* since
# Aura's navbar.scss was deleted (§3.1).  P6 wires them up for real.
METHODE_TOPBAR_BG = "#000000"
METHODE_TOPBAR_TEXT = "#FFFFFF"
# Card / form-sheet surface: the palette's paper white on the #F4F7FE page.
# (Was the measured #F2F2F2 on the old warm page, until 19.0.1.7.0.)
METHODE_CARD_BG = "#FFFFFF"
# ⚠ THESE WERE AURA'S FOUR SATURATED HUES (#2F6BFF blue, #EF4444 red, #F59E0B
# amber, #22C55E green) and they are now the brand's own ramp: ink, secondary
# ink, the single orange accent, warm raised surface.  THEME_PLAN §13.2 forbids
# dropping four saturated hues on a monochrome-plus-orange brand, and P8's
# dashboard honours that — its stat tiles take emphasis from the SIZE of the
# figure, not from a tile colour.
#
# ⚠ AND NOTHING CURRENTLY READS THEM.  Grep for `--tbt-dashboard-card-` : the
# variables are injected on every page load (twice — see views/web_assets.xml,
# which server-renders them for backend AND frontend) and consumed by no
# stylesheet, because the Aura dashboard SCSS that used them was deleted in
# §3.4.  They are kept rather than removed because the Theme Settings dialog
# still reads and writes the fields, so deleting the columns would break a
# working screen to tidy four dead variables.  Re-seeding them costs nothing and
# means that if anything ever does consume them — or an administrator simply
# opens the colour pickers — what comes out is the brand rather than Aura.
DEFAULT_DASHBOARD_CARD_1 = METHODE_TEXT
DEFAULT_DASHBOARD_CARD_2 = METHODE_TEXT_SECONDARY
DEFAULT_DASHBOARD_CARD_3 = DEFAULT_BRAND
DEFAULT_DASHBOARD_CARD_4 = METHODE_BG_SECONDARY
DEFAULT_SIDEBAR_DARKNESS = 70
DEFAULT_LOGIN_BRAND_COPY = (
    "Your all-in-one business platform. Manage sales, inventory,\n"
    "accounting, HR, and more — connected in a single ERP built\n"
    "to grow with your company."
)
DEFAULT_LOGIN_BRAND_FOOT = "{company_name}. All rights reserved."


def _hex_to_rgb_triplet(hex_color):
    value = (hex_color or DEFAULT_BRAND).lstrip("#")
    return ",".join(str(int(value[i:i + 2], 16)) for i in (0, 2, 4))


def _darken_hex(hex_color, factor=0.55):
    value = (hex_color or DEFAULT_BRAND).lstrip("#")
    rgb = [int(value[i:i + 2], 16) for i in (0, 2, 4)]
    dark_rgb = [max(0, min(255, int(channel * factor))) for channel in rgb]
    return "#%02X%02X%02X" % tuple(dark_rgb)


def _blend_hex(base_hex, target_hex, ratio):
    ratio = max(0.0, min(1.0, float(ratio or 0.0)))
    base = base_hex.lstrip("#")
    target = target_hex.lstrip("#")
    base_rgb = [int(base[i:i + 2], 16) for i in (0, 2, 4)]
    target_rgb = [int(target[i:i + 2], 16) for i in (0, 2, 4)]
    mixed = [int(round(base_rgb[i] + (target_rgb[i] - base_rgb[i]) * ratio)) for i in range(3)]
    return "#%02X%02X%02X" % tuple(mixed)


def _rgba(color_rgb, alpha):
    alpha = max(0.0, min(1.0, float(alpha or 0.0)))
    alpha_str = ("%.3f" % alpha).rstrip("0").rstrip(".")
    return "rgba(%s, %s)" % (color_rgb, alpha_str)


class ResCompany(models.Model):
    _inherit = "res.company"

    tbt_brand_color = fields.Char(
        string="Theme Brand Color",
        default=DEFAULT_BRAND,
        help="Primary brand color for the backend theme, in #RRGGBB format.",
    )
    tbt_brand_color_rgb = fields.Char(
        string="Theme Brand Color RGB",
        compute="_compute_tbt_brand_palette",
        store=True,
    )
    tbt_brand_color_dark = fields.Char(
        string="Theme Brand Color Dark",
        compute="_compute_tbt_brand_palette",
        store=True,
    )
    tbt_sidebar_dark_mode = fields.Boolean(
        string="Dark Sidebar",
        default=False,
        help="Use a darker sidebar palette for better contrast in the navigation area.",
    )
    tbt_sidebar_dark_color = fields.Char(
        string="Dark Sidebar Base Color",
        default="#1E2433",
        help="Base hue for the dark sidebar. The theme derives a deep dark shade from this colour. "
             "Default #1E2433 gives the classic dark navy look.",
    )

    tbt_topbar_bg = fields.Char(
        string="Topbar Background",
        default=METHODE_TOPBAR_BG,
        help="Background colour of the top navigation bar.",
    )
    tbt_topbar_text = fields.Char(
        string="Topbar Text Color",
        default=METHODE_TOPBAR_TEXT,
        help="Text and icon colour used inside the top bar.",
    )

    tbt_content_bg = fields.Char(
        string="Content Background",
        default=METHODE_BG_PRIMARY,
        help="Background of the main content area (list, kanban, form views).",
    )
    tbt_card_bg = fields.Char(
        string="Card / Form Surface",
        default=METHODE_CARD_BG,
        help="Background of form sheets, cards and panel surfaces.",
    )
    tbt_dashboard_card_1_color = fields.Char(
        string="Dashboard Card 1 Color",
        default=DEFAULT_DASHBOARD_CARD_1,
        help="Accent background color for the first dashboard stat card.",
    )
    tbt_dashboard_card_2_color = fields.Char(
        string="Dashboard Card 2 Color",
        default=DEFAULT_DASHBOARD_CARD_2,
        help="Accent background color for the second dashboard stat card.",
    )
    tbt_dashboard_card_3_color = fields.Char(
        string="Dashboard Card 3 Color",
        default=DEFAULT_DASHBOARD_CARD_3,
        help="Accent background color for the third dashboard stat card.",
    )
    tbt_dashboard_card_4_color = fields.Char(
        string="Dashboard Card 4 Color",
        default=DEFAULT_DASHBOARD_CARD_4,
        help="Accent background color for the fourth dashboard stat card.",
    )
    tbt_dashboard_card_solid = fields.Boolean(
        string="Solid Dashboard Cards",
        default=False,
        help="Use flat solid backgrounds on dashboard stat cards instead of the soft gradient/circle pattern.",
    )

    tbt_login_split_enabled = fields.Boolean(
        string="Login Split Screen",
        default=True,
        help="Show the branded split-screen layout on the login page.",
    )
    tbt_login_show_signup = fields.Boolean(
        string="Show Create Account Link",
        default=True,
        help="Show the create account link on the login page.",
    )
    tbt_login_brand_copy = fields.Text(
        string="Login Brand Copy",
        default=DEFAULT_LOGIN_BRAND_COPY,
        help="Descriptive text shown in the branded login panel.",
    )
    tbt_login_brand_foot = fields.Text(
        string="Login Brand Footer",
        default=DEFAULT_LOGIN_BRAND_FOOT,
        help="Footer text shown in the branded login panel. Use {company_name} as a placeholder for the active company name.",
    )
    tbt_login_background_image = fields.Image(
        string="Login Background Image",
        max_width=1920,
        max_height=1920,
        help="Optional background image for the left branded panel of the split login page.",
    )
    tbt_login_background_enabled = fields.Boolean(
        string="Use Login Background Image",
        default=True,
        help="Enable the uploaded image on the left split panel.",
    )
    tbt_login_background_pattern = fields.Boolean(
        string="Show Login Circular Pattern",
        default=True,
        help="Show circular ring patterns on the left split panel when image is used.",
    )

    tbt_loading_enabled = fields.Boolean(
        string="Custom Loading Indicator",
        default=True,
        help="Enable custom theme styling for the global loading indicator.",
    )
    tbt_loading_text = fields.Char(
        string="Loading Text Color",
        default="#FFFFFF",
        help="Text and spinner colour used by the loading indicator.",
    )
    tbt_loading_style = fields.Selection(
        selection=[
            ("arc", "Arc"),
            ("dual_arc", "Dual Arc"),
            ("spinner", "Spinner"),
            ("sun", "Sun"),
            ("dots", "Dots"),
            ("quad", "Quad"),
        ],
        string="Loading Style",
        default="arc",
        help="Visual style of the loading spinner.",
    )
    tbt_high_contrast = fields.Boolean(
        string="High Contrast",
        default=False,
        help="Enable stronger contrast in form fields by restoring visible borders.",
    )
    tbt_sidebar_bg = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_border = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_text = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_text_muted = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_surface = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_surface_hover = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_surface_active = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_active_text = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_active_border = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_icon = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_icon_hover = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_icon_active = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_icon_bg = fields.Char(compute="_compute_tbt_brand_palette", store=True)
    tbt_sidebar_brand_bg = fields.Char(compute="_compute_tbt_brand_palette", store=True)

    @api.depends("tbt_brand_color", "tbt_sidebar_dark_mode", "tbt_sidebar_dark_color")
    def _compute_tbt_brand_palette(self):
        for company in self:
            color = (company.tbt_brand_color or DEFAULT_BRAND).strip()
            if not HEX_COLOR_RE.match(color):
                color = DEFAULT_BRAND
            darkness = DEFAULT_SIDEBAR_DARKNESS
            darkness_ratio = darkness / 100.0
            company.tbt_brand_color_rgb = _hex_to_rgb_triplet(color)
            company.tbt_brand_color_dark = _darken_hex(color, factor=0.70)

            if company.tbt_sidebar_dark_mode:
                dark_base = (company.tbt_sidebar_dark_color or "#1E2433").strip()
                if not HEX_COLOR_RE.match(dark_base):
                    dark_base = "#1E2433"
                bg      = _darken_hex(dark_base, factor=0.55)
                bg_deep = _darken_hex(dark_base, factor=0.35)

                company.tbt_sidebar_bg = bg
                company.tbt_sidebar_border = _rgba("255, 255, 255", 0.14 + (darkness_ratio * 0.10))
                company.tbt_sidebar_text = _blend_hex("#D6DEF0", "#F7FAFF", min(1.0, 0.15 + (darkness_ratio * 0.65)))
                company.tbt_sidebar_text_muted = _blend_hex("#96A4C2", "#C5D1EA", min(1.0, 0.20 + (darkness_ratio * 0.50)))
                company.tbt_sidebar_surface = _rgba("255, 255, 255", 0.04 + ((1.0 - darkness_ratio) * 0.03))
                company.tbt_sidebar_surface_hover = _rgba("255, 255, 255", 0.10 + (darkness_ratio * 0.04))
                company.tbt_sidebar_surface_active = _rgba("255, 255, 255", 0.14 + (darkness_ratio * 0.06))
                company.tbt_sidebar_active_text = "#F7FAFF"
                company.tbt_sidebar_active_border = _rgba("255, 255, 255", 0.45)
                company.tbt_sidebar_icon = _blend_hex("#A9B6D3", "#E2EBFF", min(1.0, 0.20 + (darkness_ratio * 0.60)))
                company.tbt_sidebar_icon_hover = company.tbt_sidebar_text
                company.tbt_sidebar_icon_active = "#FFFFFF"
                company.tbt_sidebar_icon_bg = _rgba(company.tbt_brand_color_rgb, 0.20 + (darkness_ratio * 0.04))
                company.tbt_sidebar_brand_bg = bg_deep
            else:
                company.tbt_sidebar_bg = "#f1f2f4"
                company.tbt_sidebar_border = "rgba(171, 173, 175, .15)"
                company.tbt_sidebar_text = "#555b70"
                company.tbt_sidebar_text_muted = "#8a8e98"
                company.tbt_sidebar_surface = "rgba(255, 255, 255, .7)"
                company.tbt_sidebar_surface_hover = "#ffffff"
                company.tbt_sidebar_surface_active = "#ffffff"
                company.tbt_sidebar_active_text = "#0c0f0f"
                company.tbt_sidebar_active_border = "rgba(%s, .45)" % company.tbt_brand_color_rgb
                company.tbt_sidebar_icon = "#6e7380"
                company.tbt_sidebar_icon_hover = "#4f5564"
                company.tbt_sidebar_icon_active = company.tbt_brand_color
                company.tbt_sidebar_icon_bg = "rgba(%s, .10)" % company.tbt_brand_color_rgb
                company.tbt_sidebar_brand_bg = "#f6f6f6"

    @api.constrains(
        "tbt_brand_color", "tbt_topbar_bg", "tbt_topbar_text",
        "tbt_content_bg", "tbt_card_bg", "tbt_loading_text",
        "tbt_dashboard_card_1_color", "tbt_dashboard_card_2_color",
        "tbt_dashboard_card_3_color", "tbt_dashboard_card_4_color",
    )
    def _check_tbt_brand_color(self):
        fields_to_check = [
            ("tbt_brand_color", "Brand color"),
            ("tbt_topbar_bg",   "Topbar background"),
            ("tbt_topbar_text", "Topbar text color"),
            ("tbt_content_bg",  "Content background"),
            ("tbt_card_bg",     "Card background"),
            ("tbt_loading_text", "Loading text color"),
            ("tbt_dashboard_card_1_color", "Dashboard card 1 color"),
            ("tbt_dashboard_card_2_color", "Dashboard card 2 color"),
            ("tbt_dashboard_card_3_color", "Dashboard card 3 color"),
            ("tbt_dashboard_card_4_color", "Dashboard card 4 color"),
        ]
        for company in self:
            for fname, label in fields_to_check:
                value = (getattr(company, fname) or "").strip()
                if value and not HEX_COLOR_RE.match(value):
                    raise ValidationError(
                        f"{label} must be a valid HEX value like #242424."
                    )
