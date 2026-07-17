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
            "or household view you want kept apart.",
        ),
        (
            "02",
            "Accounts",
            "In Edit data, add the accounts you care about: current, savings, ISA, "
            "pension, credit card, mortgage, and so on. Mark debts clearly; they "
            "reduce net worth.",
        ),
        (
            "03",
            "Balances",
            "On Snapshots, pick a date and enter balances for as many accounts as "
            "you can. One date is one snapshot of your position. Incomplete dates "
            "skew charts.",
        ),
        (
            "04",
            "Income",
            "Add a fixed source for salary or a retainer (yearly or monthly). "
            "Use variable sources for freelance or gigs, and log receipts when "
            "you are paid. You do not need every bank movement.",
        ),
        (
            "05",
            "Check Overview",
            "Net worth, tax-year progress, and income by source appear once "
            "accounts, snapshots, and income exist. Allowances update when you "
            "log contribution transactions.",
        ),
        (
            "06",
            "Optional layers",
            "Holdings for investments you want named. Recurring for subscriptions "
            "and standing orders. Tax & tools for England calculators. Export from "
            "View data when you want a CSV backup.",
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
            "<strong>Routine</strong>"
            "<p>Update balances when something material changes, or on a fixed "
            "cadence (for example month-end). Log variable income when paid. "
            "Record a pay change when salary moves in the same role; do not invent "
            "a second job source for a rise.</p>",
            sanitize=False,
        )


def _how_it_works() -> None:
    topics = [
        (
            "Net worth",
            "Assets minus liabilities from the latest balance on each account. "
            "Standing orders that only move money between your own accounts do "
            "not change net worth by themselves.",
        ),
        (
            "Snapshots",
            "A snapshot is every account balance you recorded for one date. "
            "View data groups by date for that reason. Saving on Edit data writes "
            "one line per account you filled in.",
        ),
        (
            "Fixed income",
            "Expected yearly or monthly amounts are pro-rated across the UK tax "
            "year for Overview totals. Enter the rate you intend to track "
            "(usually gross annual for employment). Yearly and monthly toggles "
            "only change the unit you type in.",
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
            "you want them visible separately.",
        ),
        (
            "Recurring items",
            "Subscriptions are outflow reminders. Standing orders are transfers; "
            "keep affects-net-worth off when money stays inside your accounts. "
            "Recurring income is a schedule, not a substitute for salary history.",
        ),
        (
            "Allowances",
            "ISA, LISA, and pension usage on Overview come from contribution "
            "transactions in the tax year, not from snapshot balances alone. "
            "If you never log contributions, usage stays at zero.",
        ),
        (
            "Tax & tools",
            "Calculators use England rates for the configured year. They are "
            "planning aids, not a Self Assessment filing. Prefills use current "
            "salary rates where available.",
        ),
        (
            "Data and export",
            "Everything sits in a local SQLite file under your documents folder "
            "for that profile. View data is read-only. Export builds a CSV zip "
            "of the main tables.",
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
            "your computer: Windows (.exe), macOS (arm64 or x64), or Linux.",
        ),
        (
            "02",
            "Open the app",
            "Put the file somewhere permanent (Desktop or Applications), then "
            "double-click it. No installer is required.",
        ),
        (
            "03",
            "First profile",
            "Create a local profile. Demo data is optional and useful for a tour. "
            "Everything stays on this machine under Documents/NysasFinancialTracker.",
        ),
        (
            "04",
            "Back up",
            "Copy that Documents folder if you want a backup or to move to another "
            "computer. Export from View data for a CSV zip of the current profile.",
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
            "If macOS says the app cannot be opened, right-click the file and "
            "choose Open, or allow it under System Settings, Privacy & Security.",
        ),
        (
            "Linux display",
            "Native windows need a desktop session and WebKitGTK (via pywebview). "
            "If the window fails, run with UK_FINANCE_BROWSER=1 and use the URL "
            "printed in the terminal.",
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
            "(Windows: scripts/pack.ps1 from PowerShell, not WSL).",
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
            "you add contribution transactions for those wrappers.",
        ),
        (
            "Interest rates on accounts",
            "Stored rates describe the product. They do not yet project future "
            "growth on Overview or in charts.",
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
