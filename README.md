# Nysa's Financial Tracker

Local-first personal finance desktop app. Track accounts, debts, investments, pensions, balance snapshots, subscriptions, standing orders, earnings, interest, and England income tax, with overview metrics, editing, and charts.

Your data stays on this computer as SQLite databases under `Documents/NysasFinancialTracker/`.

## For most people (no Python)

1. Open **Releases** on this GitHub repository.
2. Download the build for your system:

   | File | Platform |
   |------|----------|
   | `NysasFinancialTracker-Windows.exe` | Windows |
   | `NysasFinancialTracker-macOS-arm64.zip` | Apple Silicon Mac |
   | `NysasFinancialTracker-macOS-x64.zip` | Intel Mac |
   | `NysasFinancialTracker-Linux.zip` | Linux |

3. Run the app (Windows: double-click the `.exe`; macOS/Linux: unzip first). Create a profile on first launch.
4. Use the in-app **Guide** for how to enter data.

**Windows:** if SmartScreen warns, choose More info, then Run anyway.  
**macOS:** unzip the download, then open `NysasFinancialTracker.app`. If Gatekeeper blocks it, right-click Open, or allow it under Privacy & Security.  
**Linux:** unzip, then run `./NysasFinancialTracker` (`chmod +x` if needed). Native mode needs a desktop display and WebKitGTK; if needed, run with `UK_FINANCE_BROWSER=1`.

Running and storing data locally costs £0.

## Publish a release (maintainers)

Binaries for Windows, macOS, and Linux are built by GitHub Actions. You do not need three machines locally.

**Easiest (Windows PowerShell):**

```powershell
.\scripts\create-release.ps1 -Version 0.1.0
```

That creates an annotated `v0.1.0` tag and pushes it to `origin`, which starts the **Release builds** workflow and publishes a GitHub Release when builds finish.

Options:

```powershell
.\scripts\create-release.ps1 -Version 0.1.0 -DryRun    # show what would happen
.\scripts\create-release.ps1 -Version 0.1.0 -Force     # allow a dirty working tree
.\scripts\create-release.ps1 -Version 0.1.0 -SkipPush  # tag locally only
```

**Manual equivalent:**

```bash
git tag -a v0.1.0 -m "Release v0.1.0"
git push origin v0.1.0
```

You can also run the workflow manually from the Actions tab (`workflow_dispatch`) to test builds without publishing a Release (the Release job only runs on tags).

Local packaging (current OS only):

```bash
# macOS / Linux / WSL (WSL produces a Linux binary)
./scripts/pack.sh

# Windows (PowerShell on Windows, not WSL)
.\scripts\pack.ps1
```

Both call `uv run python scripts/pack.py`. Output is under `dist/`.

### Signing notes

- **macOS Gatekeeper** may warn on unsigned apps; notarisation needs an Apple Developer account.
- **Windows SmartScreen** may warn until the binary is code-signed.

Document “Open anyway” for early users; signing is optional polish.

## Run from source (developers)

Requirements: Python 3.13+, [uv](https://github.com/astral-sh/uv).

```bash
uv sync
uv run python main.py
```

This opens a native desktop window when a display is available. On first launch, create a local profile (optionally with demo data).

Optional environment variables:

```bash
# Custom data directory (default: ~/Documents/NysasFinancialTracker)
UK_FINANCE_DATA_DIR=/path/to/data uv run python main.py

# Force browser mode instead of a native window
UK_FINANCE_BROWSER=1 uv run python main.py
```

On Linux, native mode needs a desktop display and WebView libraries (via `pywebview`). If those are missing, use `UK_FINANCE_BROWSER=1`.

## Pages

| Page | Purpose |
|------|---------|
| Overview | Net worth, tax-year income, allocation, ISA/LISA/pension allowances (with optional prior usage) |
| View data | Read-only inventory; CSV export, import template, and import |
| Edit data | Snapshot balances sheet, income (expected unit + pay frequency), transactions, history, recurring |
| Visualisations | Deeper charts |
| Forecasting | Net-worth projection; optional England income-tax estimate; session-only what-ifs |
| Income report | Actual income, receipts, and ledger interest for a period (default tax YTD) |
| Tax & tools | England 2026/27 income tax estimate + single-principal interest projection |
| Guide | Getting started, behaviour notes, install help |
| Profiles | Create, open, rename, close, or delete local profiles |

## Data layout

```
Documents/NysasFinancialTracker/
  profiles.json
  <profile-slug>/
    finance.db
```

One database per profile contains:

- **Ledger** — accounts (UK savings types, Premium Bonds with assumed 3.8% prize rate by default, ISAs, pensions, debts, rates, sort codes, maturity), transactions
- **Snapshots** — point-in-time balances (debt balances are amounts owed); past dates can be reopened and edited from History
- **Income streams** — salary / freelance / gigs + receipts, with expected-amount unit, pay frequency, tax treatment, and optional UK tax band
- **Allowance baselines** — optional mid-year prior usage for ISA / LISA / pension
- **Recurring** — subscriptions, standing orders, recurring income

Investment wrappers are one balance per account (no separate stock holdings list).

**Overview** shows ISA (£20k), LISA, and pension allowance usage (contributions + prior usage). **Forecasting** projects net worth using stored rates plus an assumed growth rate (default 5%, overall or per account), optional England income tax on taxable income/interest, and session-only what-ifs. **Income report** lists actual sources and ledger interest for a chosen period (default tax year to date). **View data** can **export a CSV zip**, download an **import template**, and **import** a matching zip (appends rows; ids remapped).

LISA government bonus is **25%** (up to £1,000/year on £4,000 contributions), and LISA counts inside the £20,000 ISA limit.

## Tax notes

The tax tool uses England rates for 2026/27 from [GOV.UK income tax rates](https://www.gov.uk/income-tax-rates), [tax on dividends](https://www.gov.uk/tax-on-dividends), and [tax on savings interest](https://www.gov.uk/apply-tax-free-interest-on-savings). It covers employment, pension, property, trading, savings, dividends, and a simplified trust/fund split. National Insurance and CGT are not included yet.
