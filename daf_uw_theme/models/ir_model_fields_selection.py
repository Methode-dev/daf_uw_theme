from odoo import api, models

# French label of the notification choice "In Odoo" (QA).
INBOX_LABEL_FR = 'Dans la plateforme DAF Underwriting'


class IrModelFieldsSelection(models.Model):
    _inherit = 'ir.model.fields.selection'

    @api.model
    def _daf_seed_mail_labels(self):
        """mail already translated "In Odoo", and a module update never
        overwrites a translation: set the DAF wording here, on every update.
        Nothing to do while French is not activated (a fresh database); the
        .po entry covers a language activated later."""
        if 'fr_FR' not in dict(self.env['res.lang'].get_installed()):
            return
        inbox = self.env.ref(
            'mail.selection__res_users__notification_type__inbox', raise_if_not_found=False
        )
        if inbox:
            inbox.update_field_translations('name', {'fr_FR': INBOX_LABEL_FR})
