# -*- coding: utf-8 -*-
from odoo.exceptions import UserError


def pre_init_hook(env):
    """Block install when Aura User Dashboard is already installed."""
    env.cr.execute(
        """
        SELECT 1
          FROM ir_module_module
         WHERE name = %s
           AND state IN ('installed', 'to install', 'to upgrade')
         LIMIT 1
        """,
        ('aura_user_dashboard',),
    )
    if env.cr.fetchone():
        raise UserError(
            "Cannot install Aura Backend Theme while Aura User Dashboard is installed. "
            "Uninstall Aura User Dashboard first."
        )

# XMLID -> web_icon path in "module,relative_path" format expected by ir.ui.menu.
MENU_ICON_OVERRIDES = {
    'base.menu_administration': 'aura_backend_theme,static/src/img/settings.svg',
    'base.menu_management': 'aura_backend_theme,static/src/img/apps.svg',
    'base.menu_apps': 'aura_backend_theme,static/src/img/apps.svg',
    'base.menu_custom': 'aura_backend_theme,static/src/img/contacts.svg',
    'board.menu_board_root': 'aura_backend_theme,static/src/img/apps.svg',
    'calendar.mail_menu_calendar': 'aura_backend_theme,static/src/img/second_icons/calendar.svg',
    'contacts.menu_contacts': 'aura_backend_theme,static/src/img/contacts.svg',
    'crm.crm_menu_root': 'aura_backend_theme,static/src/img/crm.svg',
    'documents.menu_root': 'aura_backend_theme,static/src/img/second_icons/documents.svg',
    'event.event_main_menu_root': 'aura_backend_theme,static/src/img/second_icons/event.svg',
    'fleet.fleet_menu_root': 'aura_backend_theme,static/src/img/second_icons/fleet.svg',
    'hr.menu_hr_root': 'aura_backend_theme,static/src/img/hr.svg',
    'hr_attendance.menu_hr_attendance_root': 'aura_backend_theme,static/src/img/second_icons/hr_attendance.svg',
    'hr_expense.menu_hr_expense_root': 'aura_backend_theme,static/src/img/second_icons/hr_expense.svg',
    'hr_holidays.menu_hr_holidays_root': 'aura_backend_theme,static/src/img/second_icons/hr_holidays.svg',
    'hr_recruitment.menu_hr_recruitment_root': 'aura_backend_theme,static/src/img/second_icons/hr_recruitment.svg',
    'knowledge.knowledge_menu_root': 'aura_backend_theme,static/src/img/second_icons/knowledge.svg',
    'mail.menu_root_discuss': 'aura_backend_theme,static/src/img/second_icons/mail.svg',
    'maintenance.menu_maintenance_root': 'aura_backend_theme,static/src/img/second_icons/maintenance.svg',
    'marketing_automation.menu_marketing_automation_root': 'aura_backend_theme,static/src/img/second_icons/marketing_automation.svg',
    'mass_mailing.mass_mailing_menu_root': 'aura_backend_theme,static/src/img/second_icons/mass_mailing.svg',
    'mrp.menu_mrp_root': 'aura_backend_theme,static/src/img/second_icons/mrp.svg',
    'planning.planning_menu_root': 'aura_backend_theme,static/src/img/second_icons/planning.svg',
    'point_of_sale.menu_point_root': 'aura_backend_theme,static/src/img/second_icons/point_of_sale.svg',
    'pos_sale.menu_pos_sale_root': 'aura_backend_theme,static/src/img/second_icons/point_of_sale.svg',
    'project.menu_main_pm': 'aura_backend_theme,static/src/img/project.svg',
    'purchase.menu_purchase_root': 'aura_backend_theme,static/src/img/purchase.svg',
    'quality_control.menu_quality_root': 'aura_backend_theme,static/src/img/second_icons/quality.svg',
    'repair.menu_repair_root': 'aura_backend_theme,static/src/img/second_icons/repair.svg',
    'sale.sale_menu_root': 'aura_backend_theme,static/src/img/second_icons/sale.svg',
    'social.social_menu_main': 'aura_backend_theme,static/src/img/second_icons/social.svg',
    'spreadsheet_dashboard.spreadsheet_dashboard_menu_root': 'aura_backend_theme,static/src/img/second_icons/spreadsheet_dashboard.svg',
    'stock.menu_stock_root': 'aura_backend_theme,static/src/img/second_icons/stock.svg',
    'survey.menu_surveys': 'aura_backend_theme,static/src/img/second_icons/survey.svg',
    'website.menu_website_configuration': 'aura_backend_theme,static/src/img/second_icons/website.svg',
    'website.menu_website_root': 'aura_backend_theme,static/src/img/second_icons/website.svg',
    'account.menu_finance': 'aura_backend_theme,static/src/img/accounting.svg',
    'account_accountant.menu_finance': 'aura_backend_theme,static/src/img/accounting.svg',
}


def post_init_hook(env):
    """Apply icon overrides and seed theme palette for all existing companies."""
    for xmlid, web_icon in MENU_ICON_OVERRIDES.items():
        menu = env.ref(xmlid, raise_if_not_found=False)
        if menu and menu._name == 'ir.ui.menu':
            menu.write({'web_icon': web_icon})

    # Stored computed fields (tbt_brand_color_rgb, sidebar palette, …) are NULL
    # for companies that existed before this module was installed.  Force a
    # compute+flush so the correct CSS variables are emitted on the very first
    # page load — no manual save in Theme Settings required.
    companies = env['res.company'].sudo().search([])
    if companies:
        companies._compute_tbt_brand_palette()
        companies.flush_recordset()