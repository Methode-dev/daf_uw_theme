from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ChainedDatetimeMixin(models.AbstractModel):
    """Keep a start/end datetime pair coherent.

    Point the mixin at your two Datetime fields and it will:

    - default the end to ``start + _chained_datetime_hours`` when only the start
      is filled;
    - keep the end's time-of-day but move its **date** onto the start's date
      whenever the start changes, so editing the start re-syncs the day;
    - refuse an end that is not after the start.

    Usage::

        class Booking(models.Model):
            _name = 'my.booking'
            _inherit = ['chained.datetime.mixin']

            _chained_datetime_start = 'check_in'
            _chained_datetime_end = 'check_out'
            _chained_datetime_hours = 2          # optional, defaults to 1

            check_in = fields.Datetime()
            check_out = fields.Datetime()

            # Odoo's decorators need literal field names, so these two hooks stay
            # with the consumer — one line each.
            @api.onchange('check_in')
            def _onchange_check_in(self):
                self._chained_datetime_sync()

            @api.constrains('check_in', 'check_out')
            def _check_check_in_out(self):
                self._chained_datetime_check()

    ``create`` and ``write`` are handled by the mixin itself: the aligned end is
    merged into the *same* write as the start, so the constraint validates a
    coherent pair instead of the intermediate (new start, stale end) that would
    raise.

    A model that does not set the two attributes is left completely alone, so
    inheriting the mixin is never harmful on its own.
    """

    _name = "chained.datetime.mixin"
    _description = "Chained Start/End Datetime Pair"

    # Names of the two Datetime fields on the concrete model.
    _chained_datetime_start = None
    _chained_datetime_end = None
    # Duration given to the end when only the start is known.
    _chained_datetime_hours = 1

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @api.model
    def _chained_datetime_names(self):
        """``(start, end)`` field names, or ``(None, None)`` when this model does
        not use the pair (both names must exist as fields)."""
        start = self._chained_datetime_start
        end = self._chained_datetime_end
        if start in self._fields and end in self._fields:
            return start, end
        return None, None

    # ------------------------------------------------------------------
    # Alignment
    # ------------------------------------------------------------------
    def _chained_datetime_aligned_end(self, start):
        """The end this record should have for a given *start*:

        - no end yet -> ``start + _chained_datetime_hours`` (a sane default that
          also satisfies the "end after start" rule);
        - end set    -> keep its time-of-day, move its date onto the start's
          date, so editing the start re-syncs the day.

        Note: alignment is done on the stored (UTC) value, so a start right
        around UTC midnight can shift the displayed day by one — acceptable for
        same-day ranges. Keeping the end's time can also leave it before the new
        start (end 09:00 vs new start 14:00); the check then flags it for the
        user to fix rather than silently moving their value.
        """
        self.ensure_one()
        _start_name, end_name = self._chained_datetime_names()
        current_end = self[end_name] if end_name else False
        if not start:
            return current_end
        if not current_end:
            return start + timedelta(hours=self._chained_datetime_hours)
        return current_end.replace(
            year=start.year, month=start.month, day=start.day,
        )

    def _chained_datetime_sync(self):
        """In-memory alignment, for the form's onchange."""
        start_name, end_name = self._chained_datetime_names()
        if not start_name:
            return
        for record in self:
            start = record[start_name]
            if not start:
                continue
            aligned = record._chained_datetime_aligned_end(start)
            if aligned != record[end_name]:
                record[end_name] = aligned

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def _chained_datetime_check(self):
        """Raise when the end is not strictly after the start."""
        start_name, end_name = self._chained_datetime_names()
        if not start_name:
            return
        for record in self:
            start, end = record[start_name], record[end_name]
            if start and end and end <= start:
                raise ValidationError(_(
                    "%(end)s must be after %(start)s.",
                    end=self._fields[end_name].get_description(self.env)["string"],
                    start=self._fields[start_name].get_description(self.env)["string"],
                ))

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        start_name, end_name = self._chained_datetime_names()
        if start_name:
            for vals in vals_list:
                # Fresh record with a start but no end -> default the end in the
                # same create, so the values are coherent from the start.
                if vals.get(start_name) and not vals.get(end_name):
                    start = fields.Datetime.to_datetime(vals[start_name])
                    vals[end_name] = start + timedelta(
                        hours=self._chained_datetime_hours,
                    )
        return super().create(vals_list)

    def write(self, vals):
        start_name, end_name = self._chained_datetime_names()
        if not start_name or start_name not in vals:
            return super().write(vals)
        # Several records may each carry a different end, so a single merged vals
        # cannot align them all — recurse one record at a time.
        if len(self) > 1:
            for record in self:
                record.write(vals)
            return True
        # Merge the aligned end INTO the same write (only when the caller did not
        # set it itself), so the constraint validates a coherent pair instead of
        # the intermediate (new start, stale end) that would raise. The form's
        # onchange usually already put the aligned end in vals, so this is
        # skipped there.
        if vals.get(start_name) and end_name not in vals and self:
            start = fields.Datetime.to_datetime(vals[start_name])
            vals = dict(vals, **{end_name: self._chained_datetime_aligned_end(start)})
        return super().write(vals)
