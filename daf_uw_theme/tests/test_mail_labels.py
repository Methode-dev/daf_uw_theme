from odoo.addons.daf_uw_theme.models.ir_model_fields_selection import INBOX_LABEL_FR
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMailLabels(TransactionCase):
    """QA: the notification choice "In Odoo" names the DAF platform in French,
    even where mail's own translation is already there (a module update never
    overwrites one)."""

    def test_inbox_notification_label_in_french(self):
        self.env["res.lang"]._activate_lang("fr_FR")
        inbox = self.env.ref("mail.selection__res_users__notification_type__inbox")
        inbox.update_field_translations("name", {"fr_FR": "Dans Odoo"})

        self.env["ir.model.fields.selection"]._daf_seed_mail_labels()

        self.assertEqual(inbox.with_context(lang="fr_FR").name, INBOX_LABEL_FR)
