# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request

from .res_company import (
    DEFAULT_BRAND,
    DEFAULT_DASHBOARD_CARD_1,
    DEFAULT_DASHBOARD_CARD_2,
    DEFAULT_DASHBOARD_CARD_3,
    DEFAULT_DASHBOARD_CARD_4,
    METHODE_BG_PRIMARY,
    METHODE_CARD_BG,
    METHODE_TOPBAR_BG,
    METHODE_TOPBAR_TEXT,
)


class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        info = super().session_info()
        if request.session.uid:
            company = _get_active_theme_company(request)
            brand = company.tbt_brand_color or DEFAULT_BRAND
            brand_rgb = company.tbt_brand_color_rgb or _hex_to_rgb(brand)
            brand_dark = company.tbt_brand_color_dark or _darken(brand)
            info['tbt_theme'] = {
                'brand': brand,
                'brand_rgb': brand_rgb,
                'brand_dark': brand_dark,
                'topbar_bg': company.tbt_topbar_bg or METHODE_TOPBAR_BG,
                'topbar_text': company.tbt_topbar_text or METHODE_TOPBAR_TEXT,
                'content_bg': company.tbt_content_bg or METHODE_BG_PRIMARY,
                'card_bg': company.tbt_card_bg or METHODE_CARD_BG,
                'dashboard_card_1': company.tbt_dashboard_card_1_color or DEFAULT_DASHBOARD_CARD_1,
                'dashboard_card_2': company.tbt_dashboard_card_2_color or DEFAULT_DASHBOARD_CARD_2,
                'dashboard_card_3': company.tbt_dashboard_card_3_color or DEFAULT_DASHBOARD_CARD_3,
                'dashboard_card_4': company.tbt_dashboard_card_4_color or DEFAULT_DASHBOARD_CARD_4,
                'dashboard_card_pattern': not company.tbt_dashboard_card_solid,
                'loading_enabled': company.tbt_loading_enabled,
                'loading_text': company.tbt_loading_text or '#FFFFFF',
                'loading_style': company.tbt_loading_style or 'arc',
                'high_contrast': bool(company.tbt_high_contrast),
                'sidebar_bg': company.tbt_sidebar_bg or '#f1f2f4',
                'sidebar_border': company.tbt_sidebar_border or 'rgba(171, 173, 175, .15)',
                'sidebar_text': company.tbt_sidebar_text or '#555b70',
                'sidebar_text_muted': company.tbt_sidebar_text_muted or '#8a8e98',
                'sidebar_surface': company.tbt_sidebar_surface or 'rgba(255, 255, 255, .7)',
                'sidebar_surface_hover': company.tbt_sidebar_surface_hover or '#ffffff',
                'sidebar_surface_active': company.tbt_sidebar_surface_active or '#ffffff',
                'sidebar_active_text': company.tbt_sidebar_active_text or '#0c0f0f',
                'sidebar_active_border': company.tbt_sidebar_active_border or 'rgba(%s, .45)' % brand_rgb,
                'sidebar_icon': company.tbt_sidebar_icon or '#6e7380',
                'sidebar_icon_hover': company.tbt_sidebar_icon_hover or '#4f5564',
                'sidebar_icon_active': company.tbt_sidebar_icon_active or brand,
                'sidebar_icon_bg': company.tbt_sidebar_icon_bg or 'rgba(%s, .10)' % brand_rgb,
                'sidebar_brand_bg': company.tbt_sidebar_brand_bg or '#f6f6f6',
            }
        return info


def _hex_to_rgb(hex_color):
    v = (hex_color or DEFAULT_BRAND).lstrip('#')
    return ','.join(str(int(v[i:i + 2], 16)) for i in (0, 2, 4))


def _darken(hex_color, factor=0.70):
    v = (hex_color or DEFAULT_BRAND).lstrip('#')
    rgb = [max(0, min(255, int(int(v[i:i + 2], 16) * factor))) for i in (0, 2, 4)]
    return '#%02X%02X%02X' % tuple(rgb)


def _get_active_theme_company(req):
    user = req.env.user.sudo()
    active_company = req.env.company
    cookie_cids = req.httprequest.cookies.get('cids', '')
    company_id = None
    if cookie_cids:
        first_cid = cookie_cids.split(',')[0].strip()
        if first_cid.isdigit():
            company_id = int(first_cid)

    if company_id and company_id in user.company_ids.ids:
        return req.env['res.company'].sudo().browse(company_id)

    if active_company and active_company.id in user.company_ids.ids:
        return active_company.sudo()

    return user.company_id.sudo()
