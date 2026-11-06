/** @odoo-module **/

import { Component, onWillUpdateProps, useRef, useState } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { Time, is24HourFormat, parseTime } from "@web/core/l10n/time";
import { useChildRef } from "@web/core/utils/hooks";

const { DateTime } = luxon;

/**
 * A time input whose dropdown holds TWO independent scrollable columns — hours
 * on the left, minutes on the right — instead of the stock TimePicker's single
 * list of every hh:mm combination (24 x 4 = 96 rows to scroll through).
 *
 * Picking an hour and picking a minute are separate gestures, so the component
 * keeps a *pending* time while the dropdown is open and hands it to `onCommit`
 * only once, when the dropdown closes. That way a half-entered time never
 * reaches the record, and the field above never fires an onchange twice.
 *
 * `onCommit(time, complete)` — `complete` is true when the user actually
 * finished a time (both halves picked, or a full value typed and confirmed),
 * as opposed to just clicking away. The caller uses it to decide whether to
 * hand over to the next field.
 */

const HOURS = [...Array(24).keys()];

/** Hour labels follow the locale: "13" in 24h, "1 pm" in 12h. Built once. */
let hourItems = null;
function getHourItems() {
    if (!hourItems) {
        const format = is24HourFormat() ? "HH" : "h a";
        hourItems = HOURS.map((hour) => ({
            value: hour,
            label: DateTime.fromObject({ hour }).toFormat(format).toLowerCase(),
        }));
    }
    return hourItems;
}

export class HourMinutePicker extends Component {
    static template = "chained_datetime.HourMinutePicker";
    static components = { Dropdown };
    static props = {
        value: Time,
        onCommit: Function,
        rounding: { type: Number, optional: true },
        muted: { type: Boolean, optional: true },
    };
    static defaultProps = {
        rounding: 5,
        muted: false,
    };

    //-------------------------------------------------------------------------
    // Lifecycle
    //-------------------------------------------------------------------------

    setup() {
        this.inputRef = useRef("input");
        this.menuRef = useChildRef();
        this.dropdown = useDropdownState({ onClose: () => this.commit() });

        this.hours = getHourItems();
        this.minutes = [];
        for (let minute = 0; minute < 60; minute += this.props.rounding) {
            this.minutes.push({ value: minute, label: String(minute).padStart(2, "0") });
        }

        this.state = useState({
            /** @type {Time} pending value, only committed when the dropdown closes */
            time: this.props.value.copy(),
            text: this.props.value.toString(),
            valid: true,
        });
        /** Halves picked during this open session — both means "done". */
        this.picked = new Set();
        this.touched = false;
        this.complete = false;

        // Follow the record while we are not in the middle of an edit.
        onWillUpdateProps((nextProps) => {
            if (!this.dropdown.isOpen) {
                this.reset(nextProps.value);
            }
        });
    }

    //-------------------------------------------------------------------------
    // Getters
    //-------------------------------------------------------------------------

    get inputClass() {
        return {
            o_invalid: !this.state.valid,
            // The field is empty: the 12:00 shown is the default it *would* get,
            // not a value it has.
            "text-muted": this.props.muted && this.state.valid,
        };
    }

    /** Wide enough for "12:00 pm", or just "12:00" on a 24h locale. */
    get inputSize() {
        return is24HourFormat() ? 5 : 8;
    }

    //-------------------------------------------------------------------------
    // Methods
    //-------------------------------------------------------------------------

    /**
     * @param {Time} value
     */
    reset(value) {
        this.state.time = value.copy();
        this.state.text = value.toString();
        this.state.valid = true;
        this.picked.clear();
        this.touched = false;
        this.complete = false;
    }

    /**
     * @param {Time} time
     */
    setPending(time) {
        this.state.time = time;
        this.state.text = time.toString();
        this.state.valid = true;
        this.touched = true;
    }

    /**
     * Hands the pending time over. Called on every close, including the ones
     * that changed nothing, so it has to be idempotent and silent when the user
     * did not actually edit anything.
     */
    commit() {
        const { touched, complete } = this;
        this.touched = false;
        this.complete = false;
        this.picked.clear();
        if (!touched || !this.state.valid) {
            // Nothing entered, or entered and unparseable: drop it and show the
            // record's value again.
            this.reset(this.props.value);
            return;
        }
        this.props.onCommit(this.state.time.copy(), complete);
    }

    ensureOpen() {
        if (!this.dropdown.isOpen) {
            this.reset(this.props.value);
            this.dropdown.open();
        }
    }

    //-------------------------------------------------------------------------
    // Handlers
    //-------------------------------------------------------------------------

    /**
     * @param {"hour" | "minute"} part
     * @param {number} value
     */
    pick(part, value) {
        const time = this.state.time.copy();
        time[part] = value;
        this.setPending(time);
        this.picked.add(part);
        if (this.picked.size === 2) {
            // Hour and minutes both set: the user is done, close and let the
            // field chain to whatever comes next.
            this.complete = true;
            this.dropdown.close();
        }
    }

    onInput() {
        this.ensureOpen();
        this.state.valid = parseTime(this.inputRef.el.value) !== null;
    }

    onChange() {
        const time = parseTime(this.inputRef.el.value);
        if (!time) {
            this.state.valid = false;
            this.dropdown.close();
            return;
        }
        // The two columns only edit hh:mm — whatever seconds the value carried
        // stay untouched.
        time.second = this.state.time.second;
        this.setPending(time);
        this.dropdown.close();
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onKeydown(ev) {
        if (!this.dropdown.isOpen) {
            return;
        }
        switch (ev.key) {
            case "Enter": {
                // Confirming a typed time counts as finishing it.
                ev.preventDefault();
                ev.stopPropagation();
                this.complete = this.state.valid;
                this.onChange();
                break;
            }
            case "Escape": {
                ev.preventDefault();
                ev.stopPropagation();
                this.reset(this.props.value);
                this.dropdown.close();
                break;
            }
            case "Tab": {
                this.dropdown.close();
                break;
            }
        }
    }

    onOpened() {
        this.inputRef.el?.select();
        // Both columns are 24 / 12 rows tall: bring the current values in view
        // by scrolling the columns themselves, never the page.
        for (const column of this.menuRef.el?.querySelectorAll(".o_chained_hm_col") || []) {
            const active = column.querySelector(".active");
            if (active) {
                column.scrollTop =
                    active.offsetTop - (column.clientHeight - active.clientHeight) / 2;
            }
        }
    }
}
