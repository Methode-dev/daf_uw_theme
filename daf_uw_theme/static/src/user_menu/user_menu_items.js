/**
 * The "My Odoo.com Account" entry of the user menu opens accounts.odoo.com, which
 * means nothing on this platform (QA: remove it).  Done in the registry, so the
 * entry is gone for every user and no template has to be patched.
 */

import { registry } from "@web/core/registry";

registry.category("user_menuitems").remove("odoo_account");
