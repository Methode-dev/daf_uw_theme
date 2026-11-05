# chained_datetime

> **Odoo 19.0** — a datetime widget split into a date field and a time field
> that hands over to the next field, plus a mixin that keeps a start/end
> datetime pair coherent.

Built for entering a **pair** of datetimes quickly: departure / arrival,
check-in / check-out, from / to. Two independent pieces — use either or both.

---

## 1. The `chained_datetime` widget

A drop-in replacement for the stock `datetime` widget.

```xml
<field name="departure_time" widget="chained_datetime"
       options="{'next_field': 'arrival_time'}"/>
<field name="arrival_time" widget="chained_datetime"/>
```

### Two inputs, one field

The field's own space holds **a date input and a time input, side by side**:

```
Departure   [ 15/08/2026 ] [ 14:30 ]
```

The calendar popover is therefore asked for a *date*, so the stock time row — a
single dropdown listing every hh:mm combination, 96 rows at the default
rounding — never renders. The time is picked next to the date instead, from a
dropdown of **two independent scrollable columns**:

```
        ┌──────┬──────┐
        │  12  │  00  │
        │  13  │  05  │
        │ [14] │  ..  │
        │  15  │ [30] │
        │  ..  │  ..  │
        └──────┴──────┘
```

Hours scroll on the left, minutes on the right; both open scrolled to the
current value. Picking one half leaves the dropdown open, picking the second
closes it — so hours-then-minutes (or the reverse) is two clicks and done. The
input also takes a typed time (`14:30`, `1430`, `2:30pm`), confirmed with Enter.

| Behaviour | Why |
|---|---|
| Date and time get **one input each** | Setting the hour was the awkward part of the stock widget; it now has its own control instead of living at the bottom of the calendar. |
| A field with no value takes **12:00** | Picking a day alone then means noon, not "whatever time it is now". The default is shown greyed until the field actually holds a value. |
| Choosing a date **always moves to this field's time input** | The two halves are entered in the order they are read, without reaching for the mouse. "Always" is literal: confirming the day a field already holds — what an end aligned by the mixin normally is — hands over just the same, because the hand-over follows the gesture and not a change of value. Closing the calendar *without* choosing does not move the focus. |
| Finishing the time **opens the next field** (`next_field`) | Enter both halves of a range in one run. The last field names no next field, so it just closes. |
| The picker **does not reopen** after a date is applied | The focus effect that opens the picker would fire again when focus returns to the input, which reads as though the value was not taken. |
| One click still opens the picker in an editable list | The reopen suppression is scoped to the moment right after a close, so the normal one-click open is untouched. |

Registered for both forms and lists (`chained_datetime` and
`list.chained_datetime`), so the same widget name works in either.

The chain looks for its target inside the current row / dialog / form — in an
editable list it opens the sibling cell of *that* row, not the first match on the
page.

### Options

Everything the stock `datetime` widget supports, minus the range ones, plus:

| Option | Effect |
|---|---|
| `next_field` | Field whose picker opens once this one's time is set. |
| `rounding` | Minutes between two entries of the minutes column (default `5`, capped at `30`). |
| `show_time` | `False` drops the time input; the date then keeps whatever time the value carried. |
| `min_date` / `max_date` / `min_precision` / `max_precision` / `warn_future` | Passed through to the calendar, unchanged. |

---

## 2. The `chained.datetime.mixin`

Field names are yours; the mixin only needs to be told which they are.

```python
class Booking(models.Model):
    _name = 'my.booking'
    _inherit = ['chained.datetime.mixin']

    _chained_datetime_start = 'check_in'
    _chained_datetime_end = 'check_out'
    _chained_datetime_hours = 2          # optional, defaults to 1

    check_in = fields.Datetime(string="Check-in")
    check_out = fields.Datetime(string="Check-out")

    # Odoo's decorators need literal field names, so these two stay with the
    # consumer — one line each.
    @api.onchange('check_in')
    def _onchange_check_in(self):
        self._chained_datetime_sync()

    @api.constrains('check_in', 'check_out')
    def _check_check_in_out(self):
        self._chained_datetime_check()
```

What you get:

- **Default end** — a record saved with a start and no end gets
  `start + _chained_datetime_hours`.
- **Date follows the start** — moving the start moves the end's *date* while
  keeping its time-of-day, so a range never straddles the wrong day by accident.
- **End after start** — enforced by `_chained_datetime_check()`.
- **Coherent writes** — `write()` merges the aligned end into the *same* write as
  the start, so the constraint sees a valid pair instead of the intermediate
  (new start, stale end) that would raise. Multi-record writes recurse per record,
  since each may carry a different end.

### API

| Member | Purpose |
|---|---|
| `_chained_datetime_start` / `_chained_datetime_end` | Field names (class attributes). |
| `_chained_datetime_hours` | Default duration; defaults to `1`. |
| `_chained_datetime_aligned_end(start)` | The end this record should have for `start`. |
| `_chained_datetime_sync()` | In-memory alignment — call from your `@api.onchange`. |
| `_chained_datetime_check()` | Raises `ValidationError` — call from your `@api.constrains`. |
| `create` / `write` | Overridden by the mixin; nothing to do. |

A model that inherits the mixin without setting the two attributes is left
completely alone, so inheriting is never harmful on its own.

---

## Notes and limitations

- Alignment works on the **stored (UTC)** value, so a start right around UTC
  midnight can shift the displayed day by one. Fine for same-day ranges.
- Keeping the end's time-of-day can leave it before a new start (end 09:00 vs new
  start 14:00). That is deliberate: the check flags it for the user instead of
  silently moving their value.
- The widget's chain fires when the value **commits**, not on every keystroke.
  The time commits when its dropdown closes, so a half-picked time never reaches
  the record and the field writes once, not once per column.
- **No range.** `start_date_field`, `end_date_field` and `always_range` are
  dropped: the split layout has no room for a second pair of inputs, and a
  start/end pair is what the chain itself is for. Use `daterange` if you want the
  stock two-value picker.
- The two columns edit **hours and minutes only**. Seconds already on the value
  are preserved, but `show_seconds` gives you no way to set them here.
- The columns have no arrow-key navigation — the keyboard path is to type the
  time into the input.
- Setting only the time on an empty field dates it **today**, like the stock
  picker does.

## Who uses it

`planning_trip` — `planning.trip.vehicle` departure / arrival.

## License

LGPL-3 — see [`__manifest__.py`](./__manifest__.py).
