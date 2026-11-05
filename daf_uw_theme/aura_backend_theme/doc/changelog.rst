.. _changelog:

Changelog
=========

`19.0.1.0.2`
------------

* Add ``pre_init_hook`` and improve Home Dashboard widget registration bootstrap
* Improve responsive behavior across dashboard, navbar, and theme settings dialog
* Add mobile-friendly topbar menu behavior for better small-screen navigation
* Improve settings tab and tab layout responsiveness on mobile
* Refine UI layering with targeted ``z-index`` fixes (gear overlay, statusbar, and dropdowns)
* Fix intermittent CRM ``RPC_ERROR`` in dashboard stats by safely handling empty ``_read_group`` results on ``crm.lead``
* Scope Home Dashboard KPI/cards and global widgets to the active company for consistent multi-company totals
* Update business/support contact email in module description pages

`19.0.1.0.1`
------------

* Add marketplace metadata ``live_test_url`` in module manifest
* Improve marketplace description page readability in All Features section
* Harden topbar user avatar sizing to avoid oversized rendering on some
	deployed environments

`19.0.1.0.0`
------------

* Initial release of Aura Backend Theme - Community Edition
* Add branded backend shell (sidebar + topbar)
* Add login page customization and theme settings
* Add styling refinements for list, form, kanban, calendar, and discuss views
