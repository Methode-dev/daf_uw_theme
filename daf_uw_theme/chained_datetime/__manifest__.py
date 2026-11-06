{
    'name': 'Chained Datetime',
    'version': '19.0.1.0.0',
    'category': 'Technical',
    'summary': 'Split date/time datetime widget that chains to the next field, '
               'and a start/end datetime pair mixin',
    'description': """
Chained Datetime
================

Two reusable pieces for entering a **start/end datetime pair** (departure /
arrival, check-in / check-out, from / to …).

``chained_datetime`` widget (JS)
--------------------------------

A drop-in replacement for the stock ``datetime`` widget that:

- **splits the field in two inputs**, date and time, side by side in the field's
  own space. The calendar popover then holds a calendar only, and the time is
  picked from **two independent scrollable columns** (hours, minutes) instead of
  a single list of every hh:mm combination;
- **defaults the time to 12:00**, so picking a day on an empty field gives noon
  rather than the current time;
- **does not reopen** the picker right after a date is applied (the stock
  field's focus effect reopens it, which reads as the value not having been
  taken);
- **hands over**: applying the date moves to the time input, and finishing the
  time opens the field named by ``options="{'next_field': 'other_field'}"`` — so
  the start jumps straight to the end.

Works in forms and in editable lists (``list.chained_datetime`` is registered
too, so the same widget name works in both).

``chained.datetime.mixin`` (Python)
-----------------------------------

Keeps the pair coherent: the end datetime defaults to start + N hours, its date
follows the start's date when the start moves, and it must stay after the start.
The field names are yours — the mixin only needs to be told which they are.
""",
    'author': 'Méthode',
    'website': 'https://methode.dev/',
    'depends': ['web'],
    'assets': {
        'web.assets_backend': [
            'chained_datetime/static/src/fields/chained_datetime/chained_datetime.scss',
            'chained_datetime/static/src/fields/chained_datetime/hour_minute_picker.js',
            'chained_datetime/static/src/fields/chained_datetime/hour_minute_picker.xml',
            'chained_datetime/static/src/fields/chained_datetime/chained_datetime.js',
            'chained_datetime/static/src/fields/chained_datetime/chained_datetime.xml',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
