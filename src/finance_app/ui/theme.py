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

.q-btn--standard.bg-primary {
  background: var(--accent) !important;
  color: #1a1418 !important;
}

.q-tab--active .q-tab__indicator {
  background: var(--accent-2) !important;
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
