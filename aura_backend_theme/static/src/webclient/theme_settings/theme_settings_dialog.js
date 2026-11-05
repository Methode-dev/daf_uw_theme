/** @odoo-module **/
/**
 * Aura Backend Theme - Community Edition — Theme Settings Dialog
 *
 * Opens as a dialog from the sidebar footer "Theme" button.
 * Has its own mini-sidebar for navigating between setting sections.
 * Currently exposes: Brand (color + dark sidebar with custom dark hue).
 */

import { Component, useState, onWillStart } from '@odoo/owl';
import { Dialog }      from '@web/core/dialog/dialog';
import { useService }  from '@web/core/utils/hooks';
import { user }        from '@web/core/user';

const DEFAULT_BRAND      = '#0A8FDC';
const DEFAULT_DARK_COLOR = '#1E2433';
const DEFAULT_TOPBAR_BG  = '#ffffff';
const DEFAULT_TOPBAR_TXT = '#0c0f0f';
const DEFAULT_CONTENT_BG = '#F4F7FE';
const DEFAULT_CARD_BG    = '#ffffff';
const DEFAULT_DASHBOARD_CARD_1 = '#111827';
const DEFAULT_DASHBOARD_CARD_2 = '#6B7280';
const DEFAULT_DASHBOARD_CARD_3 = '#0A8FDC';
const DEFAULT_DASHBOARD_CARD_4 = '#E3E9F6';
const DEFAULT_LOGIN_BRAND_COPY = 'Your all-in-one business platform. Manage sales, inventory,\naccounting, HR, and more — connected in a single ERP built\nto grow with your company.';
const DEFAULT_LOGIN_BRAND_FOOT = '{company_name}. All rights reserved.';
const DEFAULT_LOADING_TXT = '#FFFFFF';
const DEFAULT_LOADING_STYLE = 'arc';

// Preset dark sidebar hues — each has a name, a base hex and a preview bg
// (the preview bg is the ~0.55-darkened shade shown in the swatch).
export const DARK_SIDEBAR_PRESETS = [
    { id: 'navy',     label: 'Navy',     base: '#1E2433', preview: '#101320' },
    { id: 'midnight', label: 'Midnight', base: '#0D0F1A', preview: '#070810' },
    { id: 'blue',     label: 'Blue',     base: '#1837FE', preview: '#0D1E8B' },
    { id: 'indigo',   label: 'Indigo',   base: '#3B1F8C', preview: '#201148' },
    { id: 'teal',     label: 'Teal',     base: '#0F3D3E', preview: '#082122' },
    { id: 'forest',   label: 'Forest',   base: '#1A3322', preview: '#0E1C13' },
    { id: 'crimson',  label: 'Crimson',  base: '#3D1520', preview: '#220C12' },
    { id: 'custom',   label: 'Custom',   base: null,      preview: null      },
];

export const DASHBOARD_CARD_PRESETS = [
    { id: 'aura', label: 'Aura', colors: ['#2F6BFF', '#EF4444', '#F59E0B', '#22C55E'] },
    { id: 'ocean', label: 'Ocean', colors: ['#0891B2', '#2563EB', '#14B8A6', '#22C55E'] },
    { id: 'sunset', label: 'Sunset', colors: ['#F97316', '#EF4444', '#EC4899', '#8B5CF6'] },
    { id: 'forest', label: 'Forest', colors: ['#16A34A', '#65A30D', '#0F766E', '#84CC16'] },
    { id: 'candy', label: 'Candy', colors: ['#EC4899', '#A855F7', '#06B6D4', '#F59E0B'] },
    { id: 'mono', label: 'Mono', colors: ['#334155', '#475569', '#64748B', '#94A3B8'] },
];

export class ThemeSettingsDialog extends Component {
    static template   = 'aura_backend_theme.ThemeSettingsDialog';
    static components = { Dialog };
    static props      = { close: Function };

    setup() {
        this.orm          = useService('orm');
        this.notification = useService('notification');
        this.presets      = DARK_SIDEBAR_PRESETS;
        this.dashboardPresets = DASHBOARD_CARD_PRESETS;
        this.loadingStyles = [
            { id: 'arc', label: 'Arc' },
            { id: 'dual_arc', label: 'Dual Arc' },
            { id: 'spinner', label: 'Spinner' },
            { id: 'sun', label: 'Sun' },
            { id: 'dots', label: 'Dots' },
            { id: 'quad', label: 'Quad' },
        ];

        this.state = useState({
            activeSection   : 'brand',
            companyId       : null,
            brandColor      : DEFAULT_BRAND,
            darkSidebar     : false,
            darkColor       : DEFAULT_DARK_COLOR,
            darkPresetId    : 'navy',
            topbarBg        : DEFAULT_TOPBAR_BG,
            topbarText      : DEFAULT_TOPBAR_TXT,
            contentBg       : DEFAULT_CONTENT_BG,
            cardBg          : DEFAULT_CARD_BG,
            dashboardCard1   : DEFAULT_DASHBOARD_CARD_1,
            dashboardCard2   : DEFAULT_DASHBOARD_CARD_2,
            dashboardCard3   : DEFAULT_DASHBOARD_CARD_3,
            dashboardCard4   : DEFAULT_DASHBOARD_CARD_4,
            dashboardCardPattern: true,
            loginSplit      : true,
            loginShowSignup : true,
            loginUseBackgroundImage: true,
            loginBackgroundPattern: true,
            loginBrandCopy  : DEFAULT_LOGIN_BRAND_COPY,
            loginBrandFoot  : DEFAULT_LOGIN_BRAND_FOOT,
            loginBackgroundPreviewUrl: '',
            loginBackgroundImageData: null,
            loginBackgroundHasImage: false,
            loginBackgroundRemove: false,
            loginBackgroundVersion: Date.now(),
            loginGlobalLogoData: null,
            loginGlobalLogoPreviewUrl: '',
            loginGlobalLogoHasImage: false,
            loginGlobalLogoRemove: false,
            loadingEnabled  : true,
            loadingText     : DEFAULT_LOADING_TXT,
            loadingStyle    : DEFAULT_LOADING_STYLE,
            highContrast    : false,
            saving          : false,
        });

        onWillStart(async () => {
            const companyId = user.activeCompany?.id;
            if (!companyId) return;
            const [company] = await this.orm.read(
                'res.company',
                [companyId],
                [
                    'tbt_brand_color',
                    'tbt_sidebar_dark_mode',
                    'tbt_sidebar_dark_color',
                    'tbt_topbar_bg',
                    'tbt_topbar_text',
                    'tbt_content_bg',
                    'tbt_card_bg',
                    'tbt_dashboard_card_1_color',
                    'tbt_dashboard_card_2_color',
                    'tbt_dashboard_card_3_color',
                    'tbt_dashboard_card_4_color',
                    'tbt_dashboard_card_solid',
                    'tbt_login_split_enabled',
                    'tbt_login_show_signup',
                    'tbt_login_background_enabled',
                    'tbt_login_background_pattern',
                    'tbt_login_brand_copy',
                    'tbt_login_brand_foot',
                    'tbt_login_background_image',
                    'tbt_loading_enabled',
                    'tbt_loading_text',
                    'tbt_loading_style',
                    'tbt_high_contrast',
                ],
            );
            if (company) {
                this.state.companyId = companyId;
                this.state.brandColor  = company.tbt_brand_color  || DEFAULT_BRAND;
                this.state.darkSidebar = company.tbt_sidebar_dark_mode || false;
                const savedDark = company.tbt_sidebar_dark_color || DEFAULT_DARK_COLOR;
                this.state.darkColor   = savedDark;
                this.state.darkPresetId = this._matchPreset(savedDark);
                this.state.topbarBg    = company.tbt_topbar_bg || DEFAULT_TOPBAR_BG;
                this.state.topbarText  = company.tbt_topbar_text || DEFAULT_TOPBAR_TXT;
                this.state.contentBg   = company.tbt_content_bg || DEFAULT_CONTENT_BG;
                this.state.cardBg      = company.tbt_card_bg || DEFAULT_CARD_BG;
                this.state.dashboardCard1 = company.tbt_dashboard_card_1_color || DEFAULT_DASHBOARD_CARD_1;
                this.state.dashboardCard2 = company.tbt_dashboard_card_2_color || DEFAULT_DASHBOARD_CARD_2;
                this.state.dashboardCard3 = company.tbt_dashboard_card_3_color || DEFAULT_DASHBOARD_CARD_3;
                this.state.dashboardCard4 = company.tbt_dashboard_card_4_color || DEFAULT_DASHBOARD_CARD_4;
                this.state.dashboardCardPattern = company.tbt_dashboard_card_solid !== true;
                this._applyDashboardCardPreview();
                this.state.loginSplit  = company.tbt_login_split_enabled !== false;
                this.state.loginShowSignup = company.tbt_login_show_signup !== false;
                this.state.loginUseBackgroundImage = company.tbt_login_background_enabled !== false;
                this.state.loginBackgroundPattern = company.tbt_login_background_pattern !== false;
                this.state.loginBrandCopy = company.tbt_login_brand_copy || DEFAULT_LOGIN_BRAND_COPY;
                this.state.loginBrandFoot = company.tbt_login_brand_foot || DEFAULT_LOGIN_BRAND_FOOT;
                this.state.loginBackgroundHasImage = !!company.tbt_login_background_image;
                this.state.loginBackgroundVersion = Date.now();
                this.state.loadingEnabled = company.tbt_loading_enabled !== false;
                this.state.loadingText    = company.tbt_loading_text || DEFAULT_LOADING_TXT;
                this.state.loadingStyle   = company.tbt_loading_style || DEFAULT_LOADING_STYLE;
                this.state.highContrast   = !!company.tbt_high_contrast;
            }
            const logo = await this.orm.call(
                'ir.config_parameter',
                'get_param',
                ['aura_backend_theme.tbt_login_logo_global']
            );
            if (logo) {
                this.state.loginGlobalLogoHasImage = true;
                this.state.loginGlobalLogoPreviewUrl = String(logo).startsWith('data:image')
                    ? logo
                    : `data:image/png;base64,${logo}`;
            }
        });
    }

    // ── Preset helpers ────────────────────────────────────────────────────────

    _matchPreset(hex) {
        const match = DARK_SIDEBAR_PRESETS.find(
            p => p.base && p.base.toLowerCase() === hex.toLowerCase()
        );
        return match ? match.id : 'custom';
    }

    selectDarkPreset(preset) {
        if (preset.id === 'custom') {
            this.state.darkPresetId = 'custom';
            return;
        }
        this.state.darkPresetId = preset.id;
        this.state.darkColor    = preset.base;
    }

    onDarkColorPickerChange(ev) {
        this.state.darkColor    = ev.target.value;
        this.state.darkPresetId = this._matchPreset(ev.target.value);
    }

    onDarkHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.darkColor    = val;
            this.state.darkPresetId = this._matchPreset(val);
        }
    }

    // ── Section navigation ────────────────────────────────────────────────────

    setSection(id) {
        this.state.activeSection = id;
    }

    // ── Brand color helpers ───────────────────────────────────────────────────

    onColorPickerChange(ev) {
        this.state.brandColor = ev.target.value;
    }

    onHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.brandColor = val;
        }
    }

    resetBrandColor() {
        this.state.brandColor = DEFAULT_BRAND;
    }

    // ── Dark sidebar ──────────────────────────────────────────────────────────

    toggleDarkSidebar() {
        this.state.darkSidebar = !this.state.darkSidebar;
    }

    // ── Topbar colors ───────────────────────────────────────────────────────

    onTopbarBgPickerChange(ev) {
        this.state.topbarBg = ev.target.value;
    }

    onTopbarBgHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.topbarBg = val;
        }
    }

    onTopbarTextPickerChange(ev) {
        this.state.topbarText = ev.target.value;
    }

    onTopbarTextHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.topbarText = val;
        }
    }

    resetTopbarColors() {
        this.state.topbarBg = DEFAULT_TOPBAR_BG;
        this.state.topbarText = DEFAULT_TOPBAR_TXT;
    }

    // ── Background surfaces ────────────────────────────────────────────────

    onContentBgPickerChange(ev) {
        this.state.contentBg = ev.target.value;
    }

    onContentBgHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.contentBg = val;
        }
    }

    onCardBgPickerChange(ev) {
        this.state.cardBg = ev.target.value;
    }

    onCardBgHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.cardBg = val;
        }
    }

    resetBackgroundColors() {
        this.state.contentBg = DEFAULT_CONTENT_BG;
        this.state.cardBg = DEFAULT_CARD_BG;
    }

    // ── Dashboard cards ─────────────────────────────────────────────────────

    _applyDashboardCardPreview() {
        const root = document.documentElement;
        root.style.setProperty('--tbt-dashboard-card-1', this.state.dashboardCard1 || DEFAULT_DASHBOARD_CARD_1);
        root.style.setProperty('--tbt-dashboard-card-2', this.state.dashboardCard2 || DEFAULT_DASHBOARD_CARD_2);
        root.style.setProperty('--tbt-dashboard-card-3', this.state.dashboardCard3 || DEFAULT_DASHBOARD_CARD_3);
        root.style.setProperty('--tbt-dashboard-card-4', this.state.dashboardCard4 || DEFAULT_DASHBOARD_CARD_4);
        root.style.setProperty('--tbt-dashboard-card-pattern', this.state.dashboardCardPattern ? 'pattern' : 'none');
        root.classList.toggle('tbt-dashboard-card-pattern-off', !this.state.dashboardCardPattern);
    }

    onDashboardCardPickerChange(card, ev) {
        this.state[`dashboardCard${card}`] = ev.target.value;
        this._applyDashboardCardPreview();
    }

    onDashboardCardHexInputChange(card, ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state[`dashboardCard${card}`] = val;
            this._applyDashboardCardPreview();
        }
    }

    resetDashboardCardColors() {
        this.state.dashboardCard1 = DEFAULT_DASHBOARD_CARD_1;
        this.state.dashboardCard2 = DEFAULT_DASHBOARD_CARD_2;
        this.state.dashboardCard3 = DEFAULT_DASHBOARD_CARD_3;
        this.state.dashboardCard4 = DEFAULT_DASHBOARD_CARD_4;
        this._applyDashboardCardPreview();
    }

    toggleDashboardCardPattern() {
        this.state.dashboardCardPattern = !this.state.dashboardCardPattern;
        this._applyDashboardCardPreview();
    }

    applyDashboardPreset(preset) {
        const colors = preset.colors || [];
        this.state.dashboardCard1 = colors[0] || DEFAULT_DASHBOARD_CARD_1;
        this.state.dashboardCard2 = colors[1] || DEFAULT_DASHBOARD_CARD_2;
        this.state.dashboardCard3 = colors[2] || DEFAULT_DASHBOARD_CARD_3;
        this.state.dashboardCard4 = colors[3] || DEFAULT_DASHBOARD_CARD_4;
        this._applyDashboardCardPreview();
    }

    isDashboardPresetSelected(preset) {
        const colors = preset.colors || [];
        return (
            this.state.dashboardCard1.toLowerCase() === (colors[0] || '').toLowerCase()
            && this.state.dashboardCard2.toLowerCase() === (colors[1] || '').toLowerCase()
            && this.state.dashboardCard3.toLowerCase() === (colors[2] || '').toLowerCase()
            && this.state.dashboardCard4.toLowerCase() === (colors[3] || '').toLowerCase()
        );
    }

    // ── Login page ───────────────────────────────────────────────────────────

    toggleLoginSplit() {
        this.state.loginSplit = !this.state.loginSplit;
    }

    toggleLoginShowSignup() {
        this.state.loginShowSignup = !this.state.loginShowSignup;
    }

    toggleLoginUseBackgroundImage() {
        this.state.loginUseBackgroundImage = !this.state.loginUseBackgroundImage;
    }

    toggleLoginBackgroundPattern() {
        this.state.loginBackgroundPattern = !this.state.loginBackgroundPattern;
    }

    onLoginBrandCopyInput(ev) {
        this.state.loginBrandCopy = ev.target.value;
    }

    onLoginBrandFootInput(ev) {
        this.state.loginBrandFoot = ev.target.value;
    }

    resetLoginTexts() {
        this.state.loginBrandCopy = DEFAULT_LOGIN_BRAND_COPY;
        this.state.loginBrandFoot = DEFAULT_LOGIN_BRAND_FOOT;
    }

    get loginBackgroundImageUrl() {
        if (this.state.loginBackgroundPreviewUrl) {
            return this.state.loginBackgroundPreviewUrl;
        }
        if (!this.state.loginUseBackgroundImage) {
            return '';
        }
        if (!this.state.loginBackgroundHasImage || !this.state.companyId) {
            return '';
        }
        return `/web/image/res.company/${this.state.companyId}/tbt_login_background_image?unique=${this.state.loginBackgroundVersion}`;
    }

    async onLoginBackgroundImageChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file) {
            return;
        }
        if (!file.type || !file.type.startsWith('image/')) {
            this.notification.add('Please choose a valid image file.', { type: 'warning' });
            return;
        }
        try {
            const dataUrl = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result);
                reader.onerror = () => reject(new Error('read_failed'));
                reader.readAsDataURL(file);
            });
            const encoded = String(dataUrl || '');
            const parts = encoded.split(',');
            this.state.loginBackgroundImageData = parts.length > 1 ? parts[1] : null;
            this.state.loginBackgroundPreviewUrl = encoded;
            this.state.loginBackgroundHasImage = true;
            this.state.loginBackgroundRemove = false;
            this.state.loginBackgroundVersion = Date.now();
        } catch (error) {
            this.notification.add('Failed to read selected image.', { type: 'danger' });
        }
    }

    clearLoginBackgroundImage() {
        this.state.loginBackgroundImageData = null;
        this.state.loginBackgroundPreviewUrl = '';
        this.state.loginBackgroundHasImage = false;
        this.state.loginBackgroundRemove = true;
        this.state.loginBackgroundVersion = Date.now();
    }

    get loginGlobalLogoUrl() {
        return this.state.loginGlobalLogoPreviewUrl || '';
    }

    async onLoginGlobalLogoChange(ev) {
        const file = ev.target.files && ev.target.files[0];
        if (!file || !file.type || !file.type.startsWith('image/')) return;
        const dataUrl = await new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = () => resolve(reader.result);
            reader.onerror = () => reject(new Error('read_failed'));
            reader.readAsDataURL(file);
        });
        const encoded = String(dataUrl || '');
        const parts = encoded.split(',');
        this.state.loginGlobalLogoData = encoded;
        this.state.loginGlobalLogoPreviewUrl = encoded;
        this.state.loginGlobalLogoHasImage = true;
        this.state.loginGlobalLogoRemove = false;
    }

    clearLoginGlobalLogo() {
        this.state.loginGlobalLogoData = null;
        this.state.loginGlobalLogoPreviewUrl = '';
        this.state.loginGlobalLogoHasImage = false;
        this.state.loginGlobalLogoRemove = true;
    }

    // ── Loading indicator ───────────────────────────────────────────────────

    toggleLoadingEnabled() {
        this.state.loadingEnabled = !this.state.loadingEnabled;
    }

    onLoadingTextPickerChange(ev) {
        this.state.loadingText = ev.target.value;
    }

    onLoadingTextHexInputChange(ev) {
        const val = ev.target.value.trim();
        if (/^#[0-9a-fA-F]{6}$/.test(val)) {
            this.state.loadingText = val;
        }
    }

    onLoadingStyleChange(ev) {
        this.state.loadingStyle = ev.target.value || DEFAULT_LOADING_STYLE;
    }

    resetLoadingColors() {
        this.state.loadingEnabled = true;
        this.state.loadingText = DEFAULT_LOADING_TXT;
        this.state.loadingStyle = DEFAULT_LOADING_STYLE;
    }

    // ── Accessibility ───────────────────────────────────────────────────────

    toggleHighContrast() {
        this.state.highContrast = !this.state.highContrast;
    }

    // ── Save ──────────────────────────────────────────────────────────────────

    async save() {
        const companyId = user.activeCompany?.id;
        if (!companyId) return;

        this.state.saving = true;
        try {
            const payload = {
                tbt_brand_color       : this.state.brandColor,
                tbt_sidebar_dark_mode : this.state.darkSidebar,
                tbt_sidebar_dark_color: this.state.darkColor,
                tbt_topbar_bg         : this.state.topbarBg,
                tbt_topbar_text       : this.state.topbarText,
                tbt_content_bg        : this.state.contentBg,
                tbt_card_bg           : this.state.cardBg,
                tbt_dashboard_card_1_color: this.state.dashboardCard1,
                tbt_dashboard_card_2_color: this.state.dashboardCard2,
                tbt_dashboard_card_3_color: this.state.dashboardCard3,
                tbt_dashboard_card_4_color: this.state.dashboardCard4,
                tbt_dashboard_card_solid: !this.state.dashboardCardPattern,
                tbt_login_split_enabled: this.state.loginSplit,
                tbt_login_show_signup : this.state.loginShowSignup,
                tbt_login_background_enabled: this.state.loginUseBackgroundImage,
                tbt_login_background_pattern: this.state.loginBackgroundPattern,
                tbt_login_brand_copy  : this.state.loginBrandCopy,
                tbt_login_brand_foot  : this.state.loginBrandFoot,
                tbt_loading_enabled   : this.state.loadingEnabled,
                tbt_loading_text      : this.state.loadingText,
                tbt_loading_style     : this.state.loadingStyle,
                tbt_high_contrast     : this.state.highContrast,
            };
            if (this.state.loginBackgroundImageData) {
                payload.tbt_login_background_image = this.state.loginBackgroundImageData;
            } else if (this.state.loginBackgroundRemove) {
                payload.tbt_login_background_image = false;
            }
            await this.orm.write('res.company', [companyId], payload);
            if (this.state.loginGlobalLogoData) {
                await this.orm.call(
                    'ir.config_parameter',
                    'set_param',
                    ['aura_backend_theme.tbt_login_logo_global', this.state.loginGlobalLogoData]
                );
            } else if (this.state.loginGlobalLogoRemove) {
                await this.orm.call(
                    'ir.config_parameter',
                    'set_param',
                    ['aura_backend_theme.tbt_login_logo_global', '']
                );
            }

            const [confirmed] = await this.orm.read('res.company', [companyId], [
                'tbt_dashboard_card_1_color',
                'tbt_dashboard_card_2_color',
                'tbt_dashboard_card_3_color',
                'tbt_dashboard_card_4_color',
                'tbt_dashboard_card_solid',
            ]);
            if (confirmed) {
                this.state.dashboardCard1 = confirmed.tbt_dashboard_card_1_color || DEFAULT_DASHBOARD_CARD_1;
                this.state.dashboardCard2 = confirmed.tbt_dashboard_card_2_color || DEFAULT_DASHBOARD_CARD_2;
                this.state.dashboardCard3 = confirmed.tbt_dashboard_card_3_color || DEFAULT_DASHBOARD_CARD_3;
                this.state.dashboardCard4 = confirmed.tbt_dashboard_card_4_color || DEFAULT_DASHBOARD_CARD_4;
                this.state.dashboardCardPattern = confirmed.tbt_dashboard_card_solid !== true;
                this._applyDashboardCardPreview();
            }

            this.notification.add('Theme settings saved. Reloading…', { type: 'success' });
            setTimeout(() => window.location.reload(), 800);
        } catch (e) {
            this.notification.add('Failed to save settings.', { type: 'danger' });
            this.state.saving = false;
        }
    }

    // ── Nav items ─────────────────────────────────────────────────────────────

    get navItems() {
        return [
            { id: 'brand', label: 'Brand', icon: 'fa fa-paint-brush' },
            { id: 'topbar', label: 'Top Bar', icon: 'fa fa-window-maximize' },
            { id: 'backgrounds', label: 'Backgrounds', icon: 'fa fa-clone' },
            { id: 'dashboard', label: 'Dashboard', icon: 'fa fa-chart-bar' },
            { id: 'login', label: 'Login', icon: 'fa fa-sign-in' },
            { id: 'loading', label: 'Loading', icon: 'fa fa-spinner' },
            // { id: 'accessibility', label: 'Accessibility', icon: 'fa fa-universal-access' },
        ];
    }
}
