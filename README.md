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

The RA data in `ra_dashboard.py` is sourced from the Epic Track database. When RAs change (new ones added, old ones completed), run the query below in PowerShell to pull fresh data, then update `RA_DATA` in `ra_dashboard.py`.

### PowerShell Query

Save the following as a `.ps1` file and run it, or paste directly into a PowerShell window:

```powershell
$conn = New-Object System.Data.SqlClient.SqlConnection(
    'Server=thor.epic.com;Database=Track;Integrated Security=True;TrustServerCertificate=True;'
)
$conn.Open()
$cmd = $conn.CreateCommand()

$cmd.CommandText = "
SELECT
    xpg.PACKAGE_ID,
    xpg.RA_NUM,
    xpg.TITLE,
    xpg.STATUS_C,
    xpg.CREATION_DATE,
    xpg.PACKAGE_TYPE_C,
    pt.NAME AS PACKAGE_TYPE,
    STUFF((
        SELECT ', ' + e.USER_NAME
        FROM XPG_RA_CONTACT_PER cp2
        JOIN EMP_EMPLOYEE_BASIC e ON e.USER_NUMBER = cp2.CONTACT_STAFF_ID
        WHERE cp2.PACKAGE_ID = xpg.PACKAGE_ID AND cp2.CNTCT_PERSON_TYPE_C IN (4,5)
        FOR XML PATH('')
    ), 1, 2, '') AS OWNERS,
    STUFF((
        SELECT ', ' + e2.USER_NAME
        FROM XPG_RA_CONTACT_PER cp3
        JOIN EMP_EMPLOYEE_BASIC e2 ON e2.USER_NUMBER = cp3.CONTACT_STAFF_ID
        WHERE cp3.PACKAGE_ID = xpg.PACKAGE_ID AND cp3.CNTCT_PERSON_TYPE_C = 4
        FOR XML PATH('')
    ), 1, 2, '') AS PRIMARY_OWNER
FROM XPG_NOADD_SINGLE_T xpg
LEFT JOIN ZC_PACKAGE_TYPE pt ON pt.PACKAGE_TYPE_C = xpg.PACKAGE_TYPE_C
WHERE xpg.CUSTOMER_ID = '618'              -- SSM Health
  AND xpg.STATUS_C IN (10, 20)            -- New or In Progress only
  AND EXISTS (
      SELECT 1 FROM XPG_RA_CONTACT_PER
      WHERE PACKAGE_ID = xpg.PACKAGE_ID
        AND CONTACT_STAFF_ID IN ('38098', '23858')  -- Thompson or Emanuelson
        AND CNTCT_PERSON_TYPE_C IN (4, 5)
  )
ORDER BY xpg.CREATION_DATE DESC
"

$reader = $cmd.ExecuteReader()
while ($reader.Read()) {
    Write-Host "$($reader['PACKAGE_ID'])|$($reader['RA_NUM'])|$($reader['TITLE'])|$($reader['STATUS_C'])|$($reader['CREATION_DATE'])|$($reader['PACKAGE_TYPE'])|$($reader['PRIMARY_OWNER'])|$($reader['OWNERS'])"
}
$reader.Close()
$conn.Close()
```

### Getting Environment Installation Status

To pull which non-PRD environments each RA is installed in:

```powershell
$conn = New-Object System.Data.SqlClient.SqlConnection(
    'Server=thor.epic.com;Database=Track;Integrated Security=True;TrustServerCertificate=True;'
)
$conn.Open()
$cmd = $conn.CreateCommand()

# Replace with your actual PACKAGE_IDs (comma-separated)
$pkgIds = "1912959,1909830,1909841"

$cmd.CommandText = "
SELECT
    era.PACKAGE_ID,
    env.SHORT_NAME,
    era.INSTALL_STATUS_C,
    era.INSTALL_DATE,
    era.APPLICABLE_YN,
    era.REQUIRE_W_UPGRD_YN
FROM XPG_ENV_RA_AND_REL era
JOIN SLG_RA_ENVIRONMENT env ON env.ENV_ID = era.ENV_ID
WHERE era.PACKAGE_ID IN ($pkgIds)
  AND env.CUSTOMER_ID = '618'
  AND era.APPLICABLE_YN = 'Y'
ORDER BY era.PACKAGE_ID, env.SHORT_NAME
"

$reader = $cmd.ExecuteReader()
while ($reader.Read()) {
    Write-Host "$($reader['PACKAGE_ID'])|$($reader['SHORT_NAME'])|$($reader['INSTALL_STATUS_C'])|$($reader['INSTALL_DATE'])|$($reader['REQUIRE_W_UPGRD_YN'])"
}
$reader.Close()
$conn.Close()
```

**Install status interpretation:**
- `INSTALL_STATUS_C = 3` → **done**
- `INSTALL_STATUS_C = 2` → **pending**
- `APPLICABLE_YN != 'Y'` → skip (not applicable to this env)

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
