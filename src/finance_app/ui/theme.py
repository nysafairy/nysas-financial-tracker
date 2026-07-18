"""Visual theme and shared CSS."""

from __future__ import annotations

from nicegui import ui

APP_CSS = """
@import url("https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Source+Sans+3:wght@400;500;600;700&display=swap");

:root {
  --bg: #0f1419;
  --bg-elevated: #1a222d;
  --bg-soft: #243041;
  --text: #e8eef4;
  --text-muted: #9aabbc;
  --accent: #f4b6c8;
  --accent-2: #a8d4f0;
  --accent-soft: rgba(244, 182, 200, 0.18);
  --accent-2-soft: rgba(168, 212, 240, 0.16);
  --warn: #e6c07b;
  --danger: #e08a8a;
  --border: rgba(232, 238, 244, 0.10);
  --radius: 12px;
  --font-display: "Fraunces", "Iowan Old Style", Georgia, serif;
  --font-body: "Source Sans 3", "Segoe UI", sans-serif;
  --space: 1rem;
}

html, body, #app, .q-layout, .q-page-container, .q-page, .nicegui-content {
  width: 100% !important;
  max-width: 100% !important;
  min-height: 100vh;
  box-sizing: border-box;
}

body, .q-page, .nicegui-content {
  background:
    radial-gradient(1100px 560px at 8% -8%, rgba(244, 182, 200, 0.16), transparent 55%),
    radial-gradient(900px 520px at 92% 0%, rgba(168, 212, 240, 0.14), transparent 52%),
    var(--bg) !important;
  color: var(--text);
  font-family: var(--font-body);
  margin: 0;
  padding: 0 !important;
}

.nicegui-content {
  display: flex !important;
  flex-direction: column;
}

.app-shell {
  min-height: 100vh;
  width: 100%;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  padding: 0.9rem clamp(1rem, 3vw, 2rem);
  border-bottom: 1px solid var(--border);
  background: rgba(15, 20, 25, 0.9);
  backdrop-filter: blur(10px);
  position: sticky;
  top: 0;
  z-index: 20;
  width: 100%;
}

.brand {
  font-family: var(--font-display);
  font-size: clamp(1.15rem, 2vw, 1.45rem);
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text);
  white-space: nowrap;
}

.brand span {
  color: var(--accent);
}

.nav-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  flex: 1 1 auto;
  justify-content: center;
}

.nav-link {
  color: var(--text-muted) !important;
  text-decoration: none;
  padding: 0.45rem 0.95rem;
  border-radius: 999px;
  font-weight: 500;
}

.nav-link:hover {
  background: var(--bg-soft);
  color: var(--text) !important;
}

.nav-link.active {
  background: var(--accent-soft);
  color: var(--accent) !important;
}

.page-wrap {
  flex: 1 1 auto;
  width: 100%;
  max-width: min(1400px, 100%);
  margin: 0 auto;
  padding: clamp(1rem, 2.5vw, 1.75rem) clamp(1rem, 3vw, 2rem) 2.5rem;
  box-sizing: border-box;
}

.page-title {
  font-family: var(--font-display);
  font-size: clamp(1.6rem, 3vw, 2.1rem);
  font-weight: 700;
  margin: 0 0 0.35rem;
}

.page-subtitle {
  color: var(--text-muted);
  margin: 0 0 1.5rem;
  max-width: 48rem;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.9rem;
  margin-bottom: 1.25rem;
  width: 100%;
}

.metric-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.1rem;
  min-width: 0;
}

.metric-label {
  color: var(--text-muted);
  font-size: 0.85rem;
  margin-bottom: 0.35rem;
}

.metric-value {
  font-family: var(--font-display);
  font-size: clamp(1.25rem, 2vw, 1.55rem);
  font-weight: 700;
}

.hero-metrics {
  display: grid;
  grid-template-columns: minmax(240px, 1.2fr) minmax(260px, 1fr);
  gap: 1.1rem;
  margin-bottom: 1.25rem;
  width: 100%;
}

@media (max-width: 860px) {
  .hero-metrics {
    grid-template-columns: 1fr;
  }
}

.hero-networth {
  position: relative;
  overflow: hidden;
  border-radius: 18px;
  padding: 1.4rem 1.5rem 1.35rem;
  background:
    linear-gradient(135deg, rgba(244, 182, 200, 0.22), transparent 55%),
    linear-gradient(225deg, rgba(168, 212, 240, 0.18), transparent 50%),
    var(--bg-elevated);
  border: 1px solid var(--border);
}

.hero-kicker {
  color: var(--text-muted);
  font-size: 0.85rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  margin-bottom: 0.35rem;
}

.hero-amount {
  font-family: var(--font-display);
  font-size: clamp(2.4rem, 5vw, 3.4rem);
  font-weight: 700;
  line-height: 1.05;
  margin-bottom: 0.85rem;
}

.hero-foot {
  margin-top: 1rem;
  padding-top: 0.85rem;
  border-top: 1px solid rgba(232, 238, 244, 0.08);
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.hero-delta {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 0.5rem 0.85rem;
  font-size: 0.92rem;
}

.hero-delta .up { color: var(--accent-2); font-weight: 600; }
.hero-delta .down { color: #e07a5f; font-weight: 600; }
.hero-delta .muted { color: var(--text-muted); }

.allowance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

.allowance-card {
  border-radius: 14px;
  padding: 0.95rem 1.05rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
}

.allowance-card .title {
  font-family: var(--font-display);
  font-size: 0.95rem;
  margin-bottom: 0.35rem;
}

.allowance-card .meta {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.55rem;
}

.allowance-card .used {
  font-family: var(--font-display);
  font-weight: 600;
  margin-bottom: 0.4rem;
}

.ty-progress {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.ty-progress .label {
  color: var(--text-muted);
  font-size: 0.8rem;
}

.ty-track {
  height: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  overflow: hidden;
}

.ty-fill {
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, var(--accent), var(--accent-2));
}

.spark-wrap {
  width: 100%;
  min-height: 72px;
}

.split-bar {
  display: flex;
  height: 10px;
  border-radius: 999px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  margin-bottom: 0.65rem;
}

.split-bar .assets {
  background: linear-gradient(90deg, var(--accent), #f7c9d6);
}

.split-bar .debts {
  background: linear-gradient(90deg, #e07a5f, #f0a090);
}

.split-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.split-legend strong {
  color: var(--text);
  font-weight: 600;
}

.side-stack {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.flow-panel {
  border-radius: 16px;
  padding: 1rem 1.15rem;
  background: var(--bg-elevated);
  border: 1px solid var(--border);
}

.flow-panel h3 {
  font-family: var(--font-display);
  font-size: 1rem;
  margin: 0 0 0.75rem;
  font-weight: 600;
}

.flow-row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 0.75rem;
  padding: 0.35rem 0;
  border-bottom: 1px solid rgba(232, 238, 244, 0.06);
}

.flow-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.flow-row .label {
  color: var(--text-muted);
}

.flow-row .value {
  font-family: var(--font-display);
  font-weight: 600;
}

.flow-row .value.pink { color: var(--accent); }
.flow-row .value.blue { color: var(--accent-2); }
.flow-row .value.warn { color: #e07a5f; }

.pulse-strip {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1.25rem;
}

@media (max-width: 640px) {
  .pulse-strip {
    grid-template-columns: 1fr;
  }
}

.pulse-tile {
  border-radius: 14px;
  padding: 0.95rem 1.1rem;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
}

.pulse-tile.pink {
  background: linear-gradient(160deg, rgba(244, 182, 200, 0.14), var(--bg-elevated) 70%);
}

.pulse-tile.blue {
  background: linear-gradient(160deg, rgba(168, 212, 240, 0.14), var(--bg-elevated) 70%);
}

.pulse-tile .eyebrow {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-bottom: 0.2rem;
}

.pulse-tile .figure {
  font-family: var(--font-display);
  font-size: 1.45rem;
  font-weight: 700;
}

.pulse-tile .hint {
  color: var(--text-muted);
  font-size: 0.8rem;
  margin-top: 0.25rem;
}

.inventory-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-bottom: 1.25rem;
}

.stat-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.4rem 0.75rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--border);
  font-size: 0.9rem;
}

.stat-chip b {
  color: var(--accent);
  font-family: var(--font-display);
}

.panel {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.35rem;
  margin-bottom: 1.1rem;
  width: 100%;
  box-sizing: border-box;
}

.panel-title {
  font-family: var(--font-display);
  font-size: 1.15rem;
  font-weight: 600;
  margin: 0 0 1rem;
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  width: 100%;
}

.form-stack .q-field,
.form-stack .q-checkbox,
.panel .q-field,
.panel .q-checkbox {
  margin-bottom: 0.15rem;
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-top: 0.35rem;
  padding-top: 0.35rem;
}

.form-actions .q-btn,
.panel > .q-btn {
  margin-top: 0.5rem;
}

.responsive-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 320px), 1fr));
  gap: 1.1rem;
  width: 100%;
}

.result-box {
  margin-top: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 10px;
  background: var(--accent-2-soft);
  border: 1px solid rgba(168, 212, 240, 0.28);
  color: var(--text);
  line-height: 1.55;
  white-space: pre-wrap;
}

.profile-card {
  background: var(--bg-elevated);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  cursor: pointer;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.profile-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
}

.profile-card-managed {
  cursor: default;
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
}

.profile-card-managed:hover {
  transform: none;
}

.profile-card-main {
  cursor: pointer;
}

.profile-card-actions {
  border-top: 1px solid var(--border);
  padding-top: 0.65rem;
  flex-wrap: wrap;
}

.badge-accent {
  background: color-mix(in srgb, var(--accent) 18%, transparent);
  color: var(--accent);
}

.badge {
  display: inline-block;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
  background: var(--accent-soft);
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 600;
}

.q-btn {
  margin-top: 0.15rem;
}

.q-btn.bg-primary,
.q-btn--standard.bg-primary,
.q-btn--unelevated.bg-primary {
  background: var(--accent) !important;
  color: #1a1418 !important;
}

.q-btn.bg-primary .q-btn__content,
.q-btn--unelevated.bg-primary .q-btn__content,
.q-btn-group .q-btn.bg-primary,
.q-btn-group .q-btn.bg-primary .q-btn__content,
.q-btn-toggle .q-btn.bg-primary,
.q-btn-toggle .q-btn.bg-primary .q-btn__content {
  color: #1a1418 !important;
}

/* Read-only data tables: distinct header row vs body */
.data-table .q-table__top,
.data-table .q-table__bottom {
  color: var(--text-muted);
}

.data-table .q-table thead tr,
.data-table .q-table th {
  background: #243040 !important;
  color: #f4b6c8 !important;
  font-weight: 700 !important;
  font-size: 0.78rem !important;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  border-bottom: 2px solid color-mix(in srgb, var(--accent) 45%, transparent) !important;
}

.data-table .q-table tbody td {
  color: var(--text) !important;
  font-weight: 400 !important;
  border-bottom: 1px solid rgba(232, 238, 244, 0.08) !important;
}

.data-table .q-table tbody tr:nth-child(even) td {
  background: rgba(255, 255, 255, 0.03) !important;
}

.data-table .q-table tbody tr:hover td {
  background: rgba(244, 182, 200, 0.06) !important;
}

/* Quasar file uploader header uses primary pink — keep dark text for contrast */
.q-uploader__header,
.q-uploader__header-content,
.q-uploader__title,
.q-uploader__subtitle,
.q-uploader__header .q-btn,
.q-uploader__header .q-btn__content,
.q-uploader__header .q-icon {
  color: #1a1418 !important;
}

.q-uploader__header {
  background: var(--accent) !important;
}

.q-tab--active .q-tab__indicator {
  background: var(--accent-2) !important;
}

/* Snapshot session bar */
.session-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem 1.25rem;
  padding: 0.7rem clamp(1rem, 3vw, 2rem);
  border-bottom: 1px solid var(--border);
  background: rgba(26, 34, 45, 0.92);
}

.session-bar-label {
  font-weight: 600;
  color: var(--text-muted);
  margin-right: 0.75rem;
}

.session-bar-badge {
  display: inline-block;
  font-family: var(--font-display);
  font-weight: 600;
  color: var(--accent);
  margin-right: 0.75rem;
}

.session-bar-hint {
  color: var(--text-muted);
  font-size: 0.9rem;
}

.session-bar-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 0.55rem 0.75rem;
}

.session-bar-actions .session-date {
  min-width: 10rem;
}

/* Spreadsheet / ledger edit surface */
.session-sheet {
  --sheet-bg: #cfd6e0;
  --sheet-header: #b4bfcc;
  --sheet-row: #e6ebf1;
  --sheet-row-alt: #d8e0e9;
  --sheet-ink: #141a22;
  --sheet-muted: #3d4a58;
  --sheet-line: #3d4a58;
  --sheet-border: 1px solid #3d4a58;
  --text-muted: #3d4a58;
  --text: #141a22;
  --q-primary: #f4b6c8;
  border-radius: 12px;
  padding: 0.65rem 0.75rem 0.9rem;
  background: var(--sheet-bg);
  border: var(--sheet-border);
  color: var(--sheet-ink);
}

/* Defeat Quasar dark-mode white icons inside the light sheet */
.body--dark .session-sheet .q-icon,
.session-sheet .q-icon,
.session-sheet i.q-icon,
.session-sheet .material-icons,
.session-sheet .q-field__append,
.session-sheet .q-field__prepend {
  color: #f4b6c8 !important;
  opacity: 1 !important;
}

.body--dark .session-sheet .sheet-remove .q-icon,
.session-sheet .sheet-remove .q-icon,
.session-sheet .sheet-remove.q-btn {
  color: #1c2430 !important;
}

.session-sheet .session-tabs,
.session-sheet .session-tabs.q-tabs {
  background: var(--sheet-header) !important;
  border-radius: 8px 8px 0 0;
  padding: 0;
  border: var(--sheet-border);
  box-shadow: none !important;
}

.session-sheet .q-tabs__content {
  gap: 0;
  border: none !important;
}

/* Tab scroll chevrons (often white in dark mode) */
.session-sheet .q-tabs__arrow,
.session-sheet .q-tabs__arrow .q-icon,
.body--dark .session-sheet .q-tabs__arrow,
.body--dark .session-sheet .q-tabs__arrow .q-icon {
  color: #f4b6c8 !important;
  background: var(--sheet-header) !important;
  opacity: 1 !important;
  text-shadow: none !important;
}

.session-sheet .q-tab {
  color: var(--sheet-muted) !important;
  min-height: 2.5rem;
  padding: 0 0.95rem;
  text-transform: none;
  font-weight: 600;
  border-right: var(--sheet-border);
  border-radius: 0 !important;
  border-top: none !important;
  border-bottom: none !important;
}

.session-sheet .q-tab:last-child {
  border-right: none;
}

.session-sheet .q-tab--active {
  color: var(--sheet-ink) !important;
  background: var(--sheet-row) !important;
}

.session-sheet .q-tab__indicator {
  display: none !important;
}

.session-sheet .session-tab-panels,
.session-sheet .q-tab-panels,
.session-sheet .q-panel,
.session-sheet .q-tab-panel {
  background: transparent !important;
  color: var(--sheet-ink) !important;
  padding-top: 0.75rem;
}

.session-sheet .panel {
  background: var(--sheet-row) !important;
  border: var(--sheet-border);
  color: var(--sheet-ink) !important;
  box-shadow: none !important;
  border-radius: 8px;
}

.session-sheet .panel-title {
  color: var(--sheet-ink) !important;
  font-size: 1.05rem;
  margin-bottom: 0.65rem;
}

.session-sheet .panel .q-field__label,
.session-sheet .panel .q-field__native,
.session-sheet .panel .q-field__prefix,
.session-sheet .panel .q-field__suffix,
.session-sheet .panel .q-field__input,
.session-sheet label,
.session-sheet .nicegui-label {
  color: var(--sheet-ink) !important;
}

/* Field underlines: solid black, same weight everywhere */
.session-sheet .q-field__control:before,
.session-sheet .q-field__control:after,
.session-sheet .panel .q-field__control:before,
.session-sheet .panel .q-field__control:after,
.session-sheet .sheet-add .q-field__control:before,
.session-sheet .sheet-add .q-field__control:after {
  border-bottom: var(--sheet-border) !important;
}

/* Dropdown / select / date chevrons: accent pink (beat dark-mode white) */
.body--dark .session-sheet .q-field__append .q-icon,
.body--dark .session-sheet .q-select__dropdown-icon,
.session-sheet .q-field__append .q-icon,
.session-sheet .q-select .q-field__append .q-icon,
.session-sheet .q-select__dropdown-icon,
.session-sheet .q-icon.q-select__dropdown-icon,
.session-sheet .q-field--auto-height .q-field__append .q-icon,
.session-sheet .q-btn .q-icon {
  color: #f4b6c8 !important;
  opacity: 1 !important;
}

.body--dark .session-sheet .sheet-remove .q-icon,
.session-sheet .sheet-remove .q-icon,
.session-sheet .sheet-remove.q-btn .q-icon {
  color: #1c2430 !important;
}

/* Opened select menus teleport to body — keep check icons pink */
.q-menu .q-item__section--side .q-icon {
  color: #f4b6c8 !important;
}

.session-sheet .q-table,
.session-sheet .q-table__card,
.session-sheet .q-markup-table {
  background: var(--sheet-row) !important;
  color: var(--sheet-ink) !important;
  box-shadow: none !important;
  border: var(--sheet-border);
  border-radius: 6px;
  overflow: hidden;
}

.session-sheet .q-table thead tr,
.session-sheet .q-table th {
  background: var(--sheet-header) !important;
  color: var(--sheet-ink) !important;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.03em;
  text-align: left !important;
}

.session-sheet .q-table td,
.session-sheet .q-table th {
  background: transparent !important;
  color: var(--sheet-ink) !important;
  text-align: left !important;
  border-color: var(--sheet-line) !important;
  border-width: 1px !important;
  border-style: solid !important;
  font-variant-numeric: tabular-nums;
}

.session-sheet .q-table tbody tr:nth-child(even) td {
  background: var(--sheet-row-alt) !important;
}

.session-sheet .q-table .q-btn {
  color: #9a3b3b !important;
}

.sheet-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 0.65rem 1rem;
  margin-bottom: 0.65rem;
  padding: 0.55rem 0.75rem;
  border-radius: 8px;
  background: var(--sheet-header);
  border: var(--sheet-border);
}

.sheet-toolbar strong {
  display: block;
  font-family: var(--font-display);
  font-size: 1rem;
  margin-bottom: 0.1rem;
  color: var(--sheet-ink);
}

.sheet-toolbar span {
  color: var(--sheet-muted);
  font-size: 0.85rem;
}

.sheet-toolbar-right {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.sheet-date-btn,
.session-sheet .sheet-date-btn.q-btn,
.session-sheet .sheet-date-btn .q-icon {
  color: #f4b6c8 !important;
}

/* Dialog teleports outside .session-sheet — use solid colours, not sheet variables */
.sheet-date-dialog,
.q-dialog .sheet-date-dialog.q-card {
  background: #1a222d !important;
  background-color: #1a222d !important;
  color: #e8eef4 !important;
  opacity: 1 !important;
  min-width: 18rem;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(232, 238, 244, 0.16);
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.55);
}

.sheet-date-dialog-title {
  font-family: var(--font-display);
  font-weight: 600;
  margin-bottom: 0.65rem;
  color: #e8eef4 !important;
}

.sheet-date-dialog .q-date {
  background: #1a222d !important;
  box-shadow: none !important;
}

.sheet-help {
  color: var(--sheet-muted) !important;
  margin: 0 0 0.85rem;
  max-width: 42rem;
  line-height: 1.45;
  font-size: 0.92rem;
}

.sheet-grid-wrap {
  overflow-x: auto;
  border: var(--sheet-border);
  border-radius: 0;
  background: var(--sheet-row);
}

.sheet-table {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  table-layout: fixed;
}

.sheet-table col.account { width: 42%; }
.sheet-table .sheet-th,
.sheet-table .sheet-td {
  border-bottom: var(--sheet-border);
  border-right: var(--sheet-border);
  vertical-align: middle;
}

.sheet-table .sheet-th:last-child,
.sheet-table .sheet-td:last-child {
  border-right: none;
}

.sheet-th {
  padding: 0.5rem 0.65rem;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--sheet-muted);
  background: var(--sheet-header);
  text-align: left;
}

.sheet-th .nicegui-label,
.sheet-th label {
  color: var(--sheet-muted) !important;
  font-size: inherit;
  font-weight: inherit;
}

.sheet-th-num {
  text-align: right;
  width: 8.5rem;
}

.sheet-th-action {
  width: 2.75rem;
  padding: 0 !important;
}

.sheet-td {
  padding: 0.1rem 0.35rem 0.1rem 0.5rem;
  background: var(--sheet-row);
  min-width: 0;
}

.sheet-tr:nth-child(even) .sheet-td {
  background: var(--sheet-row-alt);
}

.sheet-td-muted {
  color: var(--sheet-muted);
  font-size: 0.88rem;
  padding-left: 0.65rem !important;
}

.sheet-td-muted .nicegui-label {
  color: var(--sheet-muted) !important;
}

.sheet-td-num {
  width: 8.5rem;
  text-align: right;
}

.sheet-td-action {
  width: 2.75rem;
  text-align: center;
  padding: 0 !important;
}

.sheet-remove,
.session-sheet .sheet-remove.q-btn,
.session-sheet .sheet-remove .q-icon {
  opacity: 1 !important;
  color: #1c2430 !important;
}

.sheet-remove:hover,
.session-sheet .sheet-remove.q-btn:hover,
.session-sheet .sheet-remove:hover .q-icon {
  color: #8b1e1e !important;
  background: rgba(28, 36, 48, 0.08) !important;
}

.sheet-input {
  width: 100%;
  min-width: 0;
}

.session-sheet .sheet-input .q-field__control {
  background: transparent !important;
  color: var(--sheet-ink) !important;
  min-height: 2rem;
}

.session-sheet .sheet-input .q-field__native,
.session-sheet .sheet-input input {
  color: var(--sheet-ink) !important;
  overflow: visible;
}

.session-sheet .sheet-td-num .q-field {
  width: 100%;
}

.session-sheet .sheet-input .q-field--focused .q-field__control {
  box-shadow: inset 0 0 0 2px rgba(196, 120, 140, 0.9);
  border-radius: 3px;
}

.sheet-balance input {
  font-variant-numeric: tabular-nums;
  text-align: right;
  font-weight: 600;
}

.sheet-warn {
  margin-top: 0.55rem;
  color: #7a4e14;
  font-size: 0.88rem;
  font-weight: 600;
}

.sheet-add {
  margin-top: 0.75rem;
  padding: 0.65rem 0.75rem;
  border-radius: 8px;
  background: var(--sheet-row);
  border: var(--sheet-border);
}

.session-sheet .sheet-add .q-field__append .q-icon {
  color: var(--accent) !important;
  opacity: 1 !important;
}

.sheet-add-field {
  min-width: 8.5rem;
  flex: 1 1 8.5rem;
}

.sheet-add-field.grow {
  flex: 2 1 12rem;
}

.session-sheet .sheet-add .q-field__label,
.session-sheet .sheet-add .q-field__native {
  color: var(--sheet-ink) !important;
}

.session-sheet .sheet-toggle .q-btn.bg-primary,
.session-sheet .sheet-toggle .q-btn.bg-primary .q-btn__content {
  color: #1a1418 !important;
  background: var(--accent) !important;
}

.session-sheet .sheet-toggle .q-btn:not(.bg-primary) {
  color: var(--sheet-ink) !important;
}

.session-sheet .q-expansion-item,
.session-sheet .q-expansion-item .q-item,
.session-sheet .q-expansion-item .q-item__label,
.session-sheet .sheet-history-exp .q-item__label {
  color: var(--sheet-ink) !important;
}

.session-sheet .q-expansion-item {
  border: var(--sheet-border);
  border-radius: 0;
  margin-top: 0.45rem;
  background: rgba(255, 255, 255, 0.35);
  overflow: hidden;
}

.session-sheet .q-expansion-item .q-icon,
.session-sheet .q-expansion-item__toggle-icon {
  color: var(--accent) !important;
  opacity: 1 !important;
}

.session-sheet .sheet-history-summary {
  margin-bottom: 0.75rem;
}

.draft-banner {
  margin-bottom: 1rem;
  padding: 0.7rem 1rem;
  border-radius: 10px;
  border: 1px solid rgba(244, 182, 200, 0.35);
  background: var(--accent-soft);
  color: var(--text);
  font-size: 0.92rem;
}

/* Guide */
.guide-intro,
.guide-lead {
  color: var(--text-muted);
  max-width: 40rem;
  line-height: 1.55;
  margin: 0 0 1.25rem;
}

.guide-lead {
  display: block;
}

.guide-steps {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-bottom: 1.25rem;
}

.guide-step {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 1rem 1.15rem;
  align-items: start;
  padding: 1.05rem 1.2rem;
  border-radius: 14px;
  border: 1px solid var(--border);
  background:
    linear-gradient(120deg, var(--accent-soft), transparent 42%),
    var(--bg-elevated);
}

.guide-step-num {
  font-family: var(--font-display);
  font-size: 1.35rem;
  font-weight: 700;
  color: var(--accent);
  line-height: 1;
  min-width: 2.1rem;
}

.guide-step-body h3 {
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 600;
  margin: 0 0 0.35rem;
}

.guide-step-body p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.55;
  max-width: 46rem;
}

.guide-callout {
  padding: 1.05rem 1.2rem;
  border-radius: 14px;
  border: 1px solid rgba(168, 212, 240, 0.28);
  background: var(--accent-2-soft);
}

.guide-callout strong {
  display: block;
  font-family: var(--font-display);
  font-size: 1rem;
  font-weight: 600;
  color: var(--accent-2);
  margin-bottom: 0.4rem;
}

.guide-callout p {
  margin: 0;
  color: var(--text);
  line-height: 1.55;
  max-width: 46rem;
}

.guide-topics {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 280px), 1fr));
  gap: 0.85rem;
}

.guide-topic {
  padding: 1.05rem 1.15rem;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--bg-elevated);
  border-top: 2px solid var(--accent);
}

.guide-topic h3 {
  font-family: var(--font-display);
  font-size: 1.02rem;
  font-weight: 600;
  margin: 0 0 0.45rem;
}

.guide-topic p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.55;
  font-size: 0.95rem;
}

.guide-edges {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.guide-edge {
  display: grid;
  grid-template-columns: minmax(10rem, 14rem) 1fr;
  gap: 0.75rem 1.25rem;
  padding: 0.9rem 1.1rem;
  border-radius: 12px;
  border: 1px solid var(--border);
  background: rgba(26, 34, 45, 0.85);
}

.guide-edge h3 {
  font-family: var(--font-display);
  font-size: 0.98rem;
  font-weight: 600;
  margin: 0;
  color: var(--accent);
}

.guide-edge p {
  margin: 0;
  color: var(--text-muted);
  line-height: 1.55;
}

@media (max-width: 720px) {
  .guide-edge {
    grid-template-columns: 1fr;
    gap: 0.35rem;
  }
}
"""


def apply_theme() -> None:
    ui.add_head_html(f"<style>{APP_CSS}</style>")
    ui.colors(
        primary="#f4b6c8",
        secondary="#a8d4f0",
        accent="#f4b6c8",
        dark="#0f1419",
        positive="#a8d4f0",
        negative="#e08a8a",
        info="#a8d4f0",
        warning="#e6c07b",
    )
    ui.dark_mode().enable()
