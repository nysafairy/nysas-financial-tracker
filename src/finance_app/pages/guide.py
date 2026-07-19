"""In-app guide: getting started and how the ledger behaves."""

from __future__ import annotations

from nicegui import ui

from finance_app.pages.layout import render_shell, require_profile
from finance_app.ui.components import page_header


def register() -> None:
    @ui.page("/guide")
    def guide_page() -> None:
        if not require_profile():
            return

        with render_shell("/guide"):
            page_header(
                "Guide",
                "How to run the tracker, and how the numbers are meant to behave.",
            )

            with ui.tabs().classes("w-full") as tabs:
                tab_start = ui.tab("Getting started")
                tab_how = ui.tab("How it works")
                tab_edges = ui.tab("Edge cases")
                tab_install = ui.tab("Install")

            with ui.tab_panels(tabs, value=tab_start).classes("w-full"):
                with ui.tab_panel(tab_start):
                    _getting_started()
                with ui.tab_panel(tab_how):
                    _how_it_works()
                with ui.tab_panel(tab_edges):
                    _edge_cases()
                with ui.tab_panel(tab_install):
                    _install()


def _getting_started() -> None:
    with ui.element("div").classes("guide-intro"):
        ui.html(
            "<p>Work in this order the first time. You can refine later; "
            "the aim is a usable Overview, not a perfect ledger on day one.</p>",
            sanitize=False,
        )

    steps = [
        (
            "01",
            "Profile",
            "Each profile is a separate local database. Use one profile per person "
            "or household view you want kept apart. Use Manage profiles to open, "
            "rename, close, or delete a profile. Delete removes that folder permanently.",
        ),
        (
            "02",
            "Start a snapshot",
            "The app stays view-only until you click Start new snapshot in the bar "
            "at the top. That opens an autosaved draft session and unlocks Edit data.",
        ),
        (
            "03",
            "Balances sheet",
            "Edit the spreadsheet of accounts for that date: name, type, provider, "
            "rates, access, bank details, notes, and balance. Add savings types such "
            "as easy access, regular saver, fixed terms, or Premium Bonds. Overview "
            "updates from the draft as you type.",
        ),
        (
            "04",
            "Save snapshot",
            "When every active account has a balance and the charts look right, "
            "click Save snapshot. That commits the date and returns you to view mode. "
            "Discard clears the draft without changing history.",
        ),
        (
            "05",
            "Income and extras",
            "While a session is open you can also log income and recurring items. "
            "For fixed pay, Yearly/Monthly is only the unit you type; Paid is how "
            "often money arrives (weekly, fortnightly, and so on). Investment "
            "wrappers (ISA, GIA, SIPP) are one balance each — there is no separate "
            "stock list. Tax & tools stay available any time.",
        ),
        (
            "06",
            "Allowances (if mid-year)",
            "Overview tracks ISA, LISA, and pension room from contribution "
            "transactions. If you already used allowance before starting this "
            "profile, use Set prior usage on Overview so remaining room is correct.",
        ),
        (
            "07",
            "Routine",
            "Start a new snapshot when balances change (for example month-end). "
            "To correct a past date, start a session then use Edit this snapshot on "
            "the History tab. Export or import a CSV zip from View data for backup "
            "or bulk load. Use Forecasting to project net worth with growth "
            "assumptions and temporary what-ifs. Use Income report for actual "
            "pay and interest over a chosen period.",
        ),
    ]

    with ui.element("div").classes("guide-steps"):
        for num, title, body in steps:
            with ui.element("div").classes("guide-step"):
                ui.html(f'<div class="guide-step-num">{num}</div>', sanitize=False)
                with ui.element("div").classes("guide-step-body"):
                    ui.html(f"<h3>{title}</h3>", sanitize=False)
                    ui.html(f"<p>{body}</p>", sanitize=False)

    with ui.element("div").classes("guide-callout"):
        ui.html(
            "<strong>Draft sessions</strong>"
            "<p>Closing the app mid-session keeps the draft. Reopen the profile and "
            "continue, or discard. Incomplete balances cannot be saved. Pay rises "
            "still use Record a pay change on the Income tab inside a session.</p>",
            sanitize=False,
        )


def _how_it_works() -> None:
    topics = [
        (
            "Profiles",
            "Manage profiles lets you switch between local databases, rename the "
            "display name (the folder id stays the same), close the current profile, "
            "or delete a profile and its data folder. Everything stays under "
            "Documents/NysasFinancialTracker on this machine.",
        ),
        (
            "Net worth",
            "Assets minus liabilities from the latest balance on each account. "
            "Standing orders that only move money between your own accounts do "
            "not change net worth by themselves.",
        ),
        (
            "Snapshots",
            "A committed snapshot is every account balance for one date, written "
            "when you Save snapshot. Until then, changes live in an autosaved draft "
            "that overlays Overview and wealth charts. Reopen a past date from "
            "History → Edit this snapshot to load that date's balances and overwrite "
            "them on save. Account product details (provider, rates, type) are live "
            "fields, not versioned per snapshot date.",
        ),
        (
            "Accounts and balances",
            "Net worth is the sum of account balances only. Cash savings types "
            "include easy access, limited access, regular saver, fixed terms "
            "(1/2/5 years), and Premium Bonds. New Premium Bonds accounts default "
            "to an assumed average prize rate of 3.8% for forecasting (prizes are "
            "not guaranteed). Stocks & Shares ISA, GIA, and SIPP are tracked as a "
            "single balance for the wrapper — not individual shares.",
        ),
        (
            "Fixed income",
            "Expected yearly or monthly amounts are the unit you type in; they are "
            "pro-rated across the UK tax year for Overview totals. Separately, Paid "
            "(weekly, bi-weekly, four-weekly, monthly, or yearly) records how often "
            "money lands. Forecasting uses the monthly equivalent of fixed pay plus "
            "recurring income, minus subscriptions.",
        ),
        (
            "Pay changes",
            "Same role, new rate: use Record a pay change with the effective date. "
            "History is stored as dated rate periods so year-to-date can split old "
            "and new pay. Creating a duplicate source for a rise will double-count.",
        ),
        (
            "Variable income",
            "Freelance and gigs count only from receipts you log. Fixed sources "
            "are not replaced by receipts; use receipts for bonuses or extras if "
            "you want them visible separately. Variable income is not auto-included "
            "in Forecasting — add it as a temporary what-if if needed.",
        ),
        (
            "Recurring items",
            "Subscriptions are outflow reminders and reduce forecast monthly surplus. "
            "Standing orders are transfers; keep affects-net-worth off when money "
            "stays inside your accounts. Recurring income is a schedule, not a "
            "substitute for salary history.",
        ),
        (
            "Forecasting",
            "The Forecasting page projects net worth month by month from latest "
            "balances (or an open draft), stored account rates, and net monthly "
            "cashflow. You must set a growth assumption for accounts without a "
            "stored rate — overall (default 5%) or per account. Optionally estimate "
            "England income tax on employment/trading/pension income and taxable "
            "interest (ISA, LISA, IFISA, and Premium Bonds are tax-free). Set tax "
            "treatment and an optional UK tax band on each income source in Edit "
            "data. Session-only what-ifs are not saved. National Insurance and "
            "inflation are not modelled.",
        ),
        (
            "Income report",
            "Income report shows actuals for a date range (default: UK tax year to "
            "date): pro-rated fixed pay, logged receipts, and ledger interest/"
            "dividends — not forecasted returns. Taxable vs tax-free interest is "
            "split by account type. An estimated tax figure for the window is shown "
            "using England 2026/27 rules.",
        ),
        (
            "Allowances",
            "Overview shows ISA (£20k across cash, S&S, LISA, and IFISA), LISA "
            "(£4k inside that £20k), and pension annual allowance. Usage comes from "
            "contribution transactions in the tax year, plus any prior usage you set "
            "manually with Set prior usage. Prior figures are per tax year.",
        ),
        (
            "Tax & tools",
            "Calculators use England rates for the configured year. They are "
            "planning aids, not a Self Assessment filing. Prefills use current "
            "salary rates where available. Interest projection there is for a "
            "manual lump sum — use Forecasting for the full portfolio, and Income "
            "report for actuals.",
        ),
        (
            "Data import and export",
            "Everything sits in a local SQLite file under your documents folder "
            "for that profile. View data is for browsing. Export builds a CSV zip "
            "using the same column schema as import. Download CSV import template "
            "for headers, example rows, and a README of allowed values. Import "
            "appends rows; ids inside the zip are remapped so links stay valid.",
        ),
    ]

    with ui.element("div").classes("guide-topics"):
        for title, body in topics:
            with ui.element("div").classes("guide-topic"):
                ui.html(f"<h3>{title}</h3>", sanitize=False)
                ui.html(f"<p>{body}</p>", sanitize=False)


def _install() -> None:
    with ui.element("div").classes("guide-intro"):
        ui.html(
            "<p>Non-technical users should run a packaged build from GitHub Releases. "
            "Python and uv are only needed if you are developing from source.</p>",
            sanitize=False,
        )

    steps = [
        (
            "01",
            "Download",
            "Open the project's GitHub Releases page. Take the file that matches "
            "your computer: Windows (.exe), or the macOS / Linux .zip.",
        ),
        (
            "02",
            "Open the app",
            "Put it somewhere permanent (Desktop or Applications). On Windows, "
            "double-click the .exe. On macOS, unzip and open NysasFinancialTracker.app. "
            "On Linux, unzip and run ./NysasFinancialTracker. No installer is required.",
        ),
        (
            "03",
            "First profile",
            "Create a local profile. Demo data is optional and useful for a tour. "
            "Everything stays on this machine under Documents/NysasFinancialTracker. "
            "Use Manage profiles later to rename, switch, or delete profiles.",
        ),
        (
            "04",
            "Back up",
            "Copy that Documents folder if you want a full backup or to move to "
            "another computer. From View data you can also export a CSV zip, or "
            "download the import template and re-import into a profile.",
        ),
    ]

    with ui.element("div").classes("guide-steps"):
        for num, title, body in steps:
            with ui.element("div").classes("guide-step"):
                ui.html(f'<div class="guide-step-num">{num}</div>', sanitize=False)
                with ui.element("div").classes("guide-step-body"):
                    ui.html(f"<h3>{title}</h3>", sanitize=False)
                    ui.html(f"<p>{body}</p>", sanitize=False)

    edges = [
        (
            "Windows SmartScreen",
            "Unsigned apps often show a blue warning. Choose More info, then "
            "Run anyway. The warning softens after reputation builds, or after "
            "code signing later.",
        ),
        (
            "macOS Gatekeeper",
            "Download the .zip, unzip it, then open NysasFinancialTracker.app. "
            "If macOS says the app cannot be opened, right-click and choose Open, "
            "or allow it under System Settings, Privacy & Security.",
        ),
        (
            "Linux display",
            "Unzip the download, then run ./NysasFinancialTracker (chmod +x if "
            "needed). Native windows need a desktop session and WebKitGTK "
            "(via pywebview). If the window fails, run with UK_FINANCE_BROWSER=1 "
            "and use the URL printed in the terminal.",
        ),
        (
            "Which Mac file",
            "Apple Silicon Macs use the arm64 build. Intel Macs use x64. "
            "About This Mac shows the chip type.",
        ),
        (
            "Developers",
            "From source: install uv, then uv sync and uv run python main.py. "
            "To cut a local binary: uv run python scripts/pack.py "
            "(Windows: scripts/pack.ps1 from PowerShell, not WSL). "
            "To publish a GitHub Release: .\\scripts\\create-release.ps1 -Version 0.1.0",
        ),
    ]

    with ui.element("div").classes("guide-edges"):
        for title, body in edges:
            with ui.element("div").classes("guide-edge"):
                ui.html(f"<h3>{title}</h3>", sanitize=False)
                ui.html(f"<p>{body}</p>", sanitize=False)


def _edge_cases() -> None:
    ui.html(
        '<p class="guide-lead">These are the usual ways the numbers go wrong. '
        "None of them are fatal if you know what the app is assuming.</p>",
        sanitize=False,
    )

    edges = [
        (
            "Partial snapshots",
            "If you omit accounts on a date, history and allocation charts carry "
            "forward incomplete pictures. Prefer fewer full dates over many thin ones.",
        ),
        (
            "Gross versus net",
            "Fixed salary is whatever figure you enter. Mixing take-home and gross "
            "across sources or tax prefills will mislead the tools.",
        ),
        (
            "Bonus and overtime",
            "A fixed rate does not include one-offs. Log a receipt, or record a "
            "short-lived rate change if you want the tax year total to include them "
            "in the pro-rata path.",
        ),
        (
            "ISA and LISA undercount",
            "Balance snapshots show what you hold. Allowance used only rises when "
            "you add contribution transactions for those wrappers, or when you set "
            "prior usage on Overview for amounts already used this tax year before "
            "you started logging here. Put LISA already used into both ISA prior "
            "(total subscriptions) and LISA prior (LISA-only).",
        ),
        (
            "Interest rates on accounts",
            "Stored rates describe the product and feed Forecasting. They do not "
            "project growth on Overview charts themselves. Premium Bonds use an "
            "assumed average prize rate (default 3.8%) — actual prizes vary.",
        ),
        (
            "Forecast assumptions",
            "Forecasting asks for an overall or per-account growth estimate "
            "(default 5%) for accounts without a stored rate. Change it; the "
            "default is only a starting point. What-ifs on that page are temporary. "
            "Tax-aware mode uses England income tax on salary and taxable interest "
            "only — not National Insurance.",
        ),
        (
            "Transfers and double counting",
            "A standing order plus a manual transfer transaction for the same move "
            "can clutter reports. Prefer one representation.",
        ),
        (
            "Pension annual allowance",
            "The Overview figure is a simplified annual allowance view. Taper and "
            "money-purchase annual allowance rules are not modelled in full.",
        ),
        (
            "Import duplicates",
            "CSV import always appends. Importing the same zip twice will create "
            "duplicate accounts and income sources unless you use a fresh profile.",
        ),
        (
            "Privacy",
            "Account numbers and balances are stored in plain text on this machine. "
            "Treat the profile folder like any other sensitive local file.",
        ),
    ]

    with ui.element("div").classes("guide-edges"):
        for title, body in edges:
            with ui.element("div").classes("guide-edge"):
                ui.html(f"<h3>{title}</h3>", sanitize=False)
                ui.html(f"<p>{body}</p>", sanitize=False)
