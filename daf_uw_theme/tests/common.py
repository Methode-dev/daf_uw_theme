from odoo.tests.common import TransactionCase


class DashboardCase(TransactionCase):
    """Shared base for dashboard tests, with one deliberately blunt helper.

    ⚠ WHY `_stamp` EXISTS — read this before writing another test that leans on
    `write_uid` or `write_date`, because both are unreliable inside a test and the
    failures look like product bugs.

    1. **write_date is the same for every record in the test.**  Odoo stamps it
       with PostgreSQL's `now()`, which returns the TRANSACTION start time — a
       constant for the whole test.  So `ORDER BY write_date DESC` has nothing to
       sort on and Postgres returns rows in whatever order it pleases.  A test
       that creates A then B and expects B first is testing luck.

    2. **write_uid belongs to whoever flushes, not whoever wrote.**  `create()`
       inserts immediately, but stored computed fields stay pending and land in a
       LATER `UPDATE` — which carries the uid of the env that happens to trigger
       the flush.  A record created by user B and then read by user A can end up
       stamped `write_uid = A`, which is how "Continue Working" appeared to leak
       another user's records when it does no such thing in production.

    Neither is a product defect: in production each request is its own
    transaction under one user, so the flush lands under that user and successive
    requests get different timestamps.  They are artefacts of doing several
    users' work inside one transaction, and the fix is to state the audit fields
    explicitly rather than hope the ORM guesses the same thing we did.
    """

    def _stamp(self, record, write_date=None, write_uid=None):
        """Force `write_date` / `write_uid` on a record, deterministically.

        FLUSH FIRST so nothing pending overwrites what we set; INVALIDATE AFTER so
        the next read comes from the database rather than a stale cache.  Both
        halves are load-bearing — without the flush the update is silently undone
        the moment the ORM writes its pending recomputes.
        """
        assignments, params = [], []
        if write_date is not None:
            assignments.append("write_date = %s")
            params.append(write_date)
        if write_uid is not None:
            assignments.append("write_uid = %s")
            params.append(write_uid)
        if not assignments:
            return record

        self.env.flush_all()
        params.append(record.id)
        self.env.cr.execute(
            # _table is internal, never user input, so the interpolation is safe.
            "UPDATE %s SET %s WHERE id = %%s" % (record._table, ", ".join(assignments)),
            params,
        )
        self.env.invalidate_all()
        return record
