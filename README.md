# Nysa's Financial Tracker

Local-first personal finance desktop app. Track accounts, debts, investments, pensions, balance snapshots, subscriptions, standing orders, earnings, interest, and England income tax, with overview metrics, editing, and charts.

Your data stays on this computer as SQLite databases under `Documents/NysasFinancialTracker/`.

## For most people (no Python)

1. Open **Releases** on this GitHub repository.
2. Download the build for your system:

   | File | Platform |
   |------|----------|
   | `NysasFinancialTracker-Windows.exe` | Windows |
   | `NysasFinancialTracker-macOS-arm64` | Apple Silicon Mac |
   | `NysasFinancialTracker-macOS-x64` | Intel Mac |
   | `NysasFinancialTracker-Linux` | Linux |

3. Double-click to run. Create a profile on first launch.
4. Use the in-app **Guide** for how to enter data.

**Windows:** if SmartScreen warns, choose More info, then Run anyway.  
**macOS:** if Gatekeeper blocks the app, right-click Open, or allow it under Privacy & Security.  
**Linux:** native mode needs a desktop display and WebKitGTK; if needed, run with `UK_FINANCE_BROWSER=1`.

Running and storing data locally costs £0.

## Publish a release (maintainers)

Binaries for Windows, macOS, and Linux are built by GitHub Actions. You do not need three machines locally.

1. Push the repo to GitHub and enable Actions.
2. Tag a version and push the tag:

   ```bash
   git tag v0.1.0
   git push origin v0.1.0
   ```

3. The **Release builds** workflow packages each OS and attaches the files to a GitHub Release for that tag.
4. You can also run the workflow manually from the Actions tab (`workflow_dispatch`) to test builds without publishing.

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
| Overview | Net worth hero, tax-year flow, allocation |
| View data | Read-only inventory of the current database |
| Edit data | Income sources (salary/freelance/gigs), accounts, snapshots, recurring |
| Visualisations | Deeper charts |
| Tax & tools | England 2026/27 income tax estimate + interest projection |
| Guide | Getting started, behaviour notes, install help |

## Data layout

```
Documents/NysasFinancialTracker/
  profiles.json
  <profile-slug>/
    finance.db
```

One database per profile contains:

- **Ledger** — accounts (including debts, rates, sort codes, maturity), holdings, transactions
- **Snapshots** — point-in-time balances (debt balances are amounts owed)
- **Income streams** — salary / freelance / gigs + receipts
- **Recurring** — subscriptions, standing orders, recurring income

**Overview** shows ISA/LISA/pension allowance usage. **View data** can **export a CSV zip** of all tables.

LISA government bonus is **25%** (up to £1,000/year on £4,000 contributions), and LISA counts inside the £20,000 adult ISA limit.

## Tax notes

The tax tool uses England rates for 2026/27 from [GOV.UK income tax rates](https://www.gov.uk/income-tax-rates), [tax on dividends](https://www.gov.uk/tax-on-dividends), and [tax on savings interest](https://www.gov.uk/apply-tax-free-interest-on-savings). It covers employment, pension, property, trading, savings, dividends, and a simplified trust/fund split. National Insurance and CGT are not included yet.
