# SSM Health RA Tracker Dashboard

A local web dashboard for tracking active Request Activities (RAs) at SSM Health, scoped to Technical Coordinator owners (Thompson / Emanuelson). Displays 24 active RAs from SSM's Sherlock Home page across four sections: Special Updates (current version), Special Updates (upgrade version), Licensing, and Other.

---

## Prerequisites

- **Python 3.x** — [Download here](https://www.python.org/downloads/)
  - During install, check **"Add Python to PATH"**
- **Network access to Epic** — must be on the Epic network or VPN
- Access to the **Track** SQL database (`thor.epic.com`)

---

## Running the Dashboard

### Option 1 — PowerShell launcher (recommended)

Double-click `Start-RADashboard.ps1`, or run it from PowerShell:

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\ra_dashboard\Start-RADashboard.ps1"
```

This will:
1. Check that Flask is installed (installs it automatically if not)
2. Start the local web server on port 5050
3. Open the dashboard in your default browser at http://localhost:5050

Press **Ctrl+C** in the PowerShell window to stop the server.

### Option 2 — Manual

```powershell
pip install flask
python ra_dashboard.py
```

Then open http://localhost:5050 in your browser.

---

## Updating RA Data from Track

All RA data lives in `ra_data.json`. A single script queries Epic Track and regenerates this file automatically — no manual editing required.

### Run the update script

```powershell
powershell -ExecutionPolicy Bypass -File "C:\path\to\ra_dashboard\Update-RAData.ps1"
```

This will:
1. Query Track for all New/In Progress RAs at SSM Health owned by Thompson or Emanuelson
2. Pull environment installation status for each RA
3. Overwrite `ra_data.json` with the latest data
4. Print a summary of how many RAs were found

Then **restart the dashboard** and **commit + push** `ra_data.json` so the rest of the team gets the update:

```powershell
# In the ra_dashboard folder:
git add ra_data.json
git commit -m "Refresh RA data from Track"
git push
```

> **Must be on Epic network or VPN** to reach `thor.epic.com`.

---

## Key Reference Values

| Item | Value |
|---|---|
| SSM Health Customer ID | `618` |
| David Thompson Staff ID | `38098` |
| Erik Emanuelson Staff ID | `23858` |
| Current Version (XVE) | May 2025 (XVE 1278) |
| Upgrade Version (XVE) | November 2025 (XVE 1280) |
| PRD Upgrade Date | April 11, 2026 |

**STATUS_C values:**
| Code | Meaning |
|---|---|
| 10 | New |
| 20 | In Progress |
| 30 | Complete |
| 40 | Voided |

---

## Notes Persistence

Notes and planned environment dates you enter in the dashboard are auto-saved to `ra_notes.json` in the same folder as `ra_dashboard.py`. This file is excluded from git (see `.gitignore`) so notes stay local to each machine and are not shared via GitHub.

---

## Updating the Dashboard Code

After editing `ra_dashboard.py`:

```powershell
cd C:\path\to\ra_dashboard
git add ra_dashboard.py
git commit -m "describe your change here"
git push
```

Others can pull your changes with:

```powershell
git pull
```
