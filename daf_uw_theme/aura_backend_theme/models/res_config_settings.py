# -*- coding: utf-8 -*-

from odoo import fields, models

from .res_company import (
    DEFAULT_BRAND,
    DEFAULT_DASHBOARD_CARD_1,
    DEFAULT_DASHBOARD_CARD_2,
    DEFAULT_DASHBOARD_CARD_3,
    DEFAULT_DASHBOARD_CARD_4,
)


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    tbt_brand_color = fields.Char(
        string="Theme Brand Color",
        related="company_id.tbt_brand_color",
        readonly=False,
    )
    tbt_sidebar_dark_mode = fields.Boolean(
        string="Dark Sidebar",
        related="company_id.tbt_sidebar_dark_mode",
        readonly=False,
    )
    tbt_sidebar_dark_color = fields.Char(
        string="Dark Sidebar Base Color",
        related="company_id.tbt_sidebar_dark_color",
        readonly=False,
    )
    tbt_topbar_bg = fields.Char(
        string="Topbar Background",
        related="company_id.tbt_topbar_bg",
        readonly=False,
    )
    tbt_topbar_text = fields.Char(
        string="Topbar Text Color",
        related="company_id.tbt_topbar_text",
        readonly=False,
    )
    tbt_content_bg = fields.Char(
        string="Content Background",
        related="company_id.tbt_content_bg",
        readonly=False,
    )
    tbt_card_bg = fields.Char(
        string="Card / Form Surface",
        related="company_id.tbt_card_bg",
        readonly=False,
    )
    tbt_dashboard_card_1_color = fields.Char(
        string="Dashboard Card 1 Color",
        related="company_id.tbt_dashboard_card_1_color",
        readonly=False,
    )
    tbt_dashboard_card_2_color = fields.Char(
        string="Dashboard Card 2 Color",
        related="company_id.tbt_dashboard_card_2_color",
        readonly=False,
    )
    tbt_dashboard_card_3_color = fields.Char(
        string="Dashboard Card 3 Color",
        related="company_id.tbt_dashboard_card_3_color",
        readonly=False,
    )
    tbt_dashboard_card_4_color = fields.Char(
        string="Dashboard Card 4 Color",
        related="company_id.tbt_dashboard_card_4_color",
        readonly=False,
    )
    tbt_dashboard_card_solid = fields.Boolean(
        string="Solid Dashboard Cards",
        related="company_id.tbt_dashboard_card_solid",
        readonly=False,
    )

    tbt_login_split_enabled = fields.Boolean(
        string="Login Split Screen",
        related="company_id.tbt_login_split_enabled",
        readonly=False,
    )
    tbt_login_show_signup = fields.Boolean(
        string="Show Create Account Link",
        related="company_id.tbt_login_show_signup",
        readonly=False,
    )
    tbt_login_background_image = fields.Image(
        string="Login Background Image",
        related="company_id.tbt_login_background_image",
        readonly=False,
    )
    tbt_login_background_enabled = fields.Boolean(
        string="Use Login Background Image",
        related="company_id.tbt_login_background_enabled",
        readonly=False,
    )
    tbt_login_background_pattern = fields.Boolean(
        string="Show Login Circular Pattern",
        related="company_id.tbt_login_background_pattern",
        readonly=False,
    )
    tbt_login_logo_global = fields.Binary(
        string="Login Logo (Global)",
    )
    tbt_loading_enabled = fields.Boolean(
        string="Custom Loading Indicator",
        related="company_id.tbt_loading_enabled",
        readonly=False,
    )
    tbt_loading_text = fields.Char(
        string="Loading Text Color",
        related="company_id.tbt_loading_text",
        readonly=False,
    )
    tbt_loading_style = fields.Selection(
        related="company_id.tbt_loading_style",
        readonly=False,
    )
    tbt_high_contrast = fields.Boolean(
        string="High Contrast",
        related="company_id.tbt_high_contrast",
        readonly=False,
    )

    def action_reset_tbt_brand_color(self):
        self.ensure_one()
        self.company_id.tbt_brand_color = DEFAULT_BRAND
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_toggle_tbt_sidebar_dark(self):
        self.ensure_one()
        self.company_id.tbt_sidebar_dark_mode = not self.company_id.tbt_sidebar_dark_mode
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_reset_tbt_dashboard_card_colors(self):
        self.ensure_one()
        self.company_id.write({
            "tbt_dashboard_card_1_color": DEFAULT_DASHBOARD_CARD_1,
            "tbt_dashboard_card_2_color": DEFAULT_DASHBOARD_CARD_2,
            "tbt_dashboard_card_3_color": DEFAULT_DASHBOARD_CARD_3,
            "tbt_dashboard_card_4_color": DEFAULT_DASHBOARD_CARD_4,
        })
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def get_values(self):
        res = super().get_values()
        logo = self.env["ir.config_parameter"].sudo().get_param(
            "aura_backend_theme.tbt_login_logo_global", default=""
        )
        if logo and isinstance(logo, str) and logo.startswith("data:image") and "," in logo:
            logo = logo.split(",", 1)[1]
        res.update({
            "tbt_login_logo_global": logo or False,
        })
        return res

    def set_values(self):
        super().set_values()
        self.env["ir.config_parameter"].sudo().set_param(
            "aura_backend_theme.tbt_login_logo_global",
            self.tbt_login_logo_global or "",
        )
