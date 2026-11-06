/** @odoo-module **/

import { onWillDestroy, onWillRender, useEffect, useRef, useState } from "@odoo/owl";
import { useDateTimePicker } from "@web/core/datetime/datetime_picker_hook";
import { areDatesEqual } from "@web/core/l10n/dates";
import { localization } from "@web/core/l10n/localization";
import { Time } from "@web/core/l10n/time";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useAutoresize } from "@web/core/utils/autoresize";
import { DateTimeField, dateTimeField } from "@web/views/fields/datetime/datetime_field";
import { listDateTimeField } from "@web/views/fields/datetime/list_datetime_field";
import { HourMinutePicker } from "./hour_minute_picker";

const { DateTime } = luxon;

/**
 * chained_datetime — a datetime field split into a date input and a time input,
 * that guides entry through a sequence of fields.
 *
 * Typically a start/end pair (departure -> arrival, check-in / check-out), but
 * nothing here is pair-specific: any field can name any other as its next one.
 *
 * Three behaviors layered on the stock datetime field:
 *
 * 1. Split entry. Date and time get one input each, side by side in the field's
 *    own space. The calendar popover is asked for a `date` (not a `datetime`),
 *    so the stock time row — a single dropdown listing every hh:mm combination —
 *    never renders; the time is picked from two independent scrollable columns
 *    instead (see HourMinutePicker). A field with no value yet takes 12:00 as
 *    its time, so picking a day alone gives a sane noon rather than "now".
 *
 * 2. One-click open, no post-Apply reopen. The focus effect below opens the
 *    picker whenever the date input gains focus — this is what makes a single
 *    click on an editable-list cell open the picker (the row-entering click
 *    focuses the cell but never reaches the not-yet-rendered input, so the
 *    service's onInputClick can't). The same effect would ALSO reopen the picker
 *    when focus returns to the input right after a date is applied. We keep the
 *    former and cancel only the latter: a short suppression window is opened the
 *    moment the picker closes (its onClose clears picker.activeInput) and
 *    consumed by the very next open attempt.
 *
 * 3. Chain. Applying a date hands over to this field's own time input; finishing
 *    the time hands over to the field named by options="{'next_field': 'x'}" —
 *    so a start/end pair is four gestures and no mouse trip. The last field of
 *    the chain names no next field, so finishing it simply closes.
 *
 * The Python side of the pair (default duration, date alignment, "end after
 * start") lives in chained.datetime.mixin — see the addon README.
 */

/** Time given to a field that has none yet — noon, never "now". */
const DEFAULT_TIME = { hour: 12, minute: 0, second: 0 };
/** Minutes between two entries of the minutes column. */
const DEFAULT_ROUNDING = 5;
/** Long enough to outlive the focus that follows a close, short enough not to
 * swallow a genuine reopen. */
const SUPPRESS_REOPEN_MS = 400;

export class ChainedDateTimeField extends DateTimeField {
    static template = "chained_datetime.ChainedDateTimeField";
    static components = { HourMinutePicker };
    static props = {
        ...DateTimeField.props,
        nextField: { type: String, optional: true },
    };

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    /**
     * Replaces DateTimeField's setup rather than extending it: the base builds a
     * datetime picker with an inline onApply we need to own (to merge the picked
     * day with the time input), and range handling this widget does not use.
     * Every getter and helper of the base is still inherited untouched.
     */
    setup() {
        this.root = useRef("root");
        this.startDate = useRef("start-date");
        this.picker = useState({ activeInput: "" });

        const getPickerProps = () => {
            const pickerProps = {
                value: this.getRecordValue(),
                // "date", not "datetime": the popover picks a day and closes,
                // the time lives in its own input next to it.
                type: "date",
                range: false,
            };
            if (this.props.maxDate) {
                pickerProps.maxDate = this.parseLimitDate(this.props.maxDate);
            }
            if (this.props.minDate) {
                pickerProps.minDate = this.parseLimitDate(this.props.minDate);
            }
            if (this.props.maxPrecision) {
                pickerProps.maxPrecision = this.props.maxPrecision;
            }
            if (this.props.minPrecision) {
                pickerProps.minPrecision = this.props.minPrecision;
            }
            return pickerProps;
        };

        const dateTimePicker = useDateTimePicker({
            target: "root",
            get pickerProps() {
                return getPickerProps();
            },
            onClose: () => {
                this.picker.activeInput = "";
                this.state.value = this.getRecordValue();
                this._datePicked = false;
            },
            onApply: () => this.commitDate(),
        });
        // Subscribes to changes made on the picker state
        this.state = useState(dateTimePicker.state);

        // Did the user *choose* a date, or did the popover just close because
        // they clicked elsewhere? The value alone cannot tell us: re-picking the
        // day a field already holds — what an end aligned by
        // chained.datetime.mixin normally is — changes nothing yet must still
        // hand over. onSelect fires on a day click and nothing else, so wrap the
        // one the service installed (functions are handed back unproxied, and
        // the props getter above never overwrites this key).
        this._datePicked = false;
        const baseOnSelect = dateTimePicker.state.onSelect;
        dateTimePicker.state.onSelect = (value, unit) => {
            this._datePicked = true;
            return baseOnSelect(value, unit);
        };

        // Wrap the focus-effect open so the post-apply reopen is swallowed once.
        const baseOpenPicker = dateTimePicker.open;
        this.openPicker = (index) => {
            if (this._suppressReopen) {
                this._suppressReopen = false;
                clearTimeout(this._reopenTimer);
                return;
            }
            return baseOpenPicker(index);
        };

        useEffect(
            () => {
                if (this.startDate.el?.dataset.field === this.picker.activeInput) {
                    this.startDate.el.focus();
                    this.openPicker(0);
                }
            },
            () => [this.startDate.el, this.picker.activeInput]
        );

        // Open the suppression window when the picker closes. Registered after
        // the effect above so that, on the render where activeInput is set
        // again, the open attempt is the one being suppressed.
        this._suppressReopen = false;
        let prevActive = this.picker.activeInput;
        useEffect(
            () => {
                const cur = this.picker.activeInput;
                if (prevActive && !cur) {
                    this._suppressReopen = true;
                    clearTimeout(this._reopenTimer);
                    // Fallback clear: if no reopen attempt consumes it (e.g.
                    // closed by clicking away), don't leave genuine opens
                    // suppressed.
                    this._reopenTimer = setTimeout(() => {
                        this._suppressReopen = false;
                    }, SUPPRESS_REOPEN_MS);
                }
                prevActive = cur;
            },
            () => [this.picker.activeInput]
        );

        onWillRender(() => this.triggerIsDirty());
        onWillDestroy(() => {
            clearTimeout(this._reopenTimer);
            clearTimeout(this._handoverTimer);
        });

        this.futureWarningMsg = _t("This date is in the future");
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    /** The time half of the field: the record's, or the 12:00 default. */
    get timeValue() {
        const value = this.props.record.data[this.props.name];
        if (value) {
            return new Time({
                hour: value.hour,
                minute: value.minute,
                second: value.second,
            });
        }
        return new Time(DEFAULT_TIME);
    }

    /** Wide enough for the locale's date format, e.g. "dd/MM/yyyy". */
    get dateInputSize() {
        return localization.dateFormat.length + 1;
    }

    get minutesRounding() {
        const rounding = this.props.rounding;
        // `show_seconds` sets rounding to 0, and the option itself may be absent
        // or unparseable. Half an hour is as coarse as a column can usefully be.
        return Number.isInteger(rounding) && rounding > 0
            ? Math.min(rounding, 30)
            : DEFAULT_ROUNDING;
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * Applies what the calendar (or the typed date) gave us — a bare day — by
     * putting the current time back on it, then hands over to the time input.
     */
    async commitDate() {
        const picked = this._datePicked;
        this._datePicked = false;
        const { name, record } = this.props;
        const current = record.data[name];
        const day = this.state.value;
        const time = this.timeValue;
        const next = day
            ? day.set({ ...time.toObject(), millisecond: 0 })
            : false;
        if (!areDatesEqual(next, current)) {
            await record.update({ [name]: next });
        }
        // Hand over on the gesture, not on the value changing — but only when
        // there was a gesture, so closing the popover by clicking somewhere else
        // does not yank the focus back here.
        if (!next || !picked) {
            return;
        }
        if (this.props.showTime) {
            this.handOver(() => this.root.el?.querySelector(".o_chained_time_input")?.focus());
        } else {
            this.chainToNextField();
        }
    }

    /**
     * @param {Time} time
     * @param {boolean} complete whether the user finished the time, as opposed
     *  to just clicking away from a half-picked one
     */
    async commitTime(time, complete) {
        const { name, record } = this.props;
        const current = record.data[name];
        // Only a time, on a field that has no date yet: today, like the stock
        // picker does.
        const next = (current || DateTime.local()).set({ ...time.toObject(), millisecond: 0 });
        if (!areDatesEqual(next, current)) {
            await record.update({ [name]: next });
        }
        if (complete) {
            this.chainToNextField();
        }
    }

    chainToNextField() {
        const anchor = this.root.el;
        if (!this.props.nextField || !anchor) {
            return;
        }
        // Scope to THIS row / dialog so we open the right sibling.
        const scope =
            anchor.closest(".modal") ||
            anchor.closest("tr") ||
            anchor.closest(".o_form_view") ||
            document;
        this.handOver(() => {
            const cell = scope.querySelector(`[name="${this.props.nextField}"]`);
            const clickable = cell && cell.querySelector("input, button");
            if (clickable) {
                clickable.focus();
                clickable.click();
            }
        });
    }

    /**
     * Defers a focus move past the re-render (and past the focus the closing
     * popover restores), so it lands on a mounted element and is not undone.
     *
     * @param {() => void} fn
     */
    handOver(fn) {
        clearTimeout(this._handoverTimer);
        this._handoverTimer = setTimeout(fn, 0);
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    onInput() {
        // Typing a date is choosing one too, so it hands over just like a click
        // on the calendar does.
        this._datePicked = true;
        super.onInput();
    }
}

export class ChainedListDateTimeField extends ChainedDateTimeField {
    setup() {
        super.setup();
        useAutoresize(this.startDate, { offset: -5, ignoreIfEmpty: true });
    }
}

function extractProps(base, fieldInfo, dynamicInfo) {
    const props = base.extractProps(fieldInfo, dynamicInfo);
    // Single value only: the split date/time layout has no room for a range, and
    // a start/end pair is what the chain itself is for.
    delete props.startDateField;
    delete props.endDateField;
    delete props.alwaysRange;
    props.nextField = fieldInfo.options.next_field;
    return props;
}

const NEXT_FIELD_OPTION = {
    label: _t("Next field to open on apply"),
    name: "next_field",
    type: "field",
};

registry.category("fields").add("chained_datetime", {
    ...dateTimeField,
    component: ChainedDateTimeField,
    extractProps: (fieldInfo, dynamicInfo) => extractProps(dateTimeField, fieldInfo, dynamicInfo),
    supportedOptions: [...(dateTimeField.supportedOptions || []), NEXT_FIELD_OPTION],
});

registry.category("fields").add("list.chained_datetime", {
    ...listDateTimeField,
    component: ChainedListDateTimeField,
    extractProps: (fieldInfo, dynamicInfo) =>
        extractProps(listDateTimeField, fieldInfo, dynamicInfo),
    supportedOptions: [...(listDateTimeField.supportedOptions || []), NEXT_FIELD_OPTION],
});
