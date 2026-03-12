# Update-RAData.ps1
# Queries Epic Track and regenerates ra_data.json with current RA and environment data.
# Run this any time RAs are added, completed, or env installs change.
# Restart the dashboard after running to see the updated data.

$ErrorActionPreference = "Stop"
$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutputFile = Join-Path $ScriptDir "ra_data.json"

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    SSM Health RA Data Refresh" -ForegroundColor White
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Connecting to Track..." -ForegroundColor Gray

$conn = New-Object System.Data.SqlClient.SqlConnection(
    'Server=thor.epic.com;Database=Track;Integrated Security=True;TrustServerCertificate=True;'
)
$conn.Open()
$cmd = $conn.CreateCommand()

# ── Step 1: Pull all New/In-Progress RAs for SSM owned by Thompson or Emanuelson ──
Write-Host "  Querying active RAs..." -ForegroundColor Gray

$cmd.CommandText = "
SELECT
    xpg.PACKAGE_ID,
    xpg.RA_NUM,
    xpg.TITLE,
    xpg.CREATION_DATE,
    xpg.REQUIRE_W_UPGRD_YN,
    ISNULL(pt.NAME, 'Other') AS PACKAGE_TYPE,
    (
        SELECT TOP 1 e.USER_NAME
        FROM XPG_RA_CONTACT_PER cp
        JOIN EMP_EMPLOYEE_BASIC e ON e.USER_NUMBER = cp.CONTACT_STAFF_ID
        WHERE cp.PACKAGE_ID = xpg.PACKAGE_ID
          AND cp.CNTCT_PERSON_TYPE_C = 4
    ) AS PRIMARY_OWNER
FROM XPG_NOADD_SINGLE_T xpg
LEFT JOIN ZC_PACKAGE_TYPE pt ON pt.PACKAGE_TYPE_C = xpg.PACKAGE_TYPE_C
WHERE xpg.CUSTOMER_ID = '618'
  AND xpg.STATUS_C IN (10, 20)
  AND EXISTS (
      SELECT 1 FROM XPG_RA_CONTACT_PER
      WHERE PACKAGE_ID = xpg.PACKAGE_ID
        AND CONTACT_STAFF_ID IN ('38098', '23858')
        AND CNTCT_PERSON_TYPE_C IN (4, 5)
  )
ORDER BY xpg.CREATION_DATE DESC
"

$ras = [ordered]@{}
$r = $cmd.ExecuteReader()
while ($r.Read()) {
    $pkgId       = [string]$r['PACKAGE_ID']
    $reqUpgrd    = if ($r['REQUIRE_W_UPGRD_YN'] -is [DBNull]) { "" } else { [string]$r['REQUIRE_W_UPGRD_YN'] }
    $pkgType     = [string]$r['PACKAGE_TYPE']
    $ras[$pkgId] = [ordered]@{
        pkg_id        = [int]$r['PACKAGE_ID']
        ra_num        = [int]$r['RA_NUM']
        title         = [string]$r['TITLE']
        created       = ([datetime]$r['CREATION_DATE']).ToString("yyyy-MM-dd")
        type          = $pkgType
        primary_owner = if ($r['PRIMARY_OWNER'] -is [DBNull]) { "" } else { [string]$r['PRIMARY_OWNER'] }
        envs          = [ordered]@{}
        upgrade_ver   = ($reqUpgrd -eq 'Y' -and $pkgType -eq 'Special Update')
    }
}
$r.Close()

if ($ras.Count -eq 0) {
    Write-Host "  ERROR: No active RAs returned. Check connection and permissions." -ForegroundColor Red
    $conn.Close()
    exit 1
}
Write-Host "  Found $($ras.Count) active RAs." -ForegroundColor Gray

# ── Step 2: Pull environment installation status for those RAs ──
Write-Host "  Querying environment installs..." -ForegroundColor Gray

$pkgIdList = ($ras.Keys) -join ","
$cmd.CommandText = "
SELECT
    era.PACKAGE_ID,
    v.ENVIRONMENT_NAME,
    slg.RA_ENV_TYPE_C,
    era.XPG_INSTALL_STATUS_C,
    era.INSTALL_DATE,
    era.RA_ENV_APPLICABLE
FROM XPG_ENV_RA_AND_REL era
JOIN SLG_RA_ENVIRONMENT slg ON slg.RA_ENVIRONMENT_ID = era.CUSTOMER_ENV_ID
JOIN v_SLG_Environments v ON v.LINE = slg.LINE AND v.CUSTOMER_NUMBER = slg.CUSTOMER_NUMBER
WHERE era.PACKAGE_ID IN ($pkgIdList)
  AND slg.CUSTOMER_NUMBER = '618'
  AND era.RA_ENV_APPLICABLE = 1
  AND slg.RA_ENV_TYPE_C NOT IN (11, 80, 99)
ORDER BY era.PACKAGE_ID, v.ENVIRONMENT_NAME
"

$r = $cmd.ExecuteReader()
while ($r.Read()) {
    $pkgId = [string]$r['PACKAGE_ID']
    if (-not $ras.Contains($pkgId)) { continue }

    # Strip 'SSM ' prefix for a compact display name (e.g. 'SSM REL' -> 'REL')
    $envName     = ([string]$r['ENVIRONMENT_NAME']) -replace '^SSM\s+', ''
    $statusC     = if ($r['XPG_INSTALL_STATUS_C'] -is [DBNull]) { -1 } else { [int]$r['XPG_INSTALL_STATUS_C'] }
    $installDate = $r['INSTALL_DATE']

    # Install status: 3 = Completed, non-null install date = done, 2 = Pending
    if ($statusC -eq 3 -or (-not ($installDate -is [DBNull]))) {
        $ras[$pkgId].envs[$envName] = "done"
    } elseif ($statusC -eq 2) {
        $ras[$pkgId].envs[$envName] = "pending"
    }
}
$r.Close()
$conn.Close()

# ── Step 3: Serialize to JSON ──
Write-Host "  Writing ra_data.json..." -ForegroundColor Gray

# Build a clean array for JSON output
$output = @()
foreach ($ra in $ras.Values) {
    # Convert envs hashtable to PSCustomObject so JSON serializes as {} not []
    $envsObj = if ($ra.envs.Count -gt 0) {
        $e = [ordered]@{}
        foreach ($k in $ra.envs.Keys) { $e[$k] = $ra.envs[$k] }
        [PSCustomObject]$e
    } else {
        [PSCustomObject]@{}
    }

    $output += [PSCustomObject]@{
        pkg_id        = $ra.pkg_id
        ra_num        = $ra.ra_num
        title         = $ra.title
        created       = $ra.created
        type          = $ra.type
        primary_owner = $ra.primary_owner
        envs          = $envsObj
        upgrade_ver   = $ra.upgrade_ver
    }
}

# Write without BOM so Python's json.load() can read it
$json = $output | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($OutputFile, $json, [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    Done! $($output.Count) RAs written." -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Restart the dashboard to load the new data." -ForegroundColor Yellow
Write-Host "  Then commit + push ra_data.json to share with the team." -ForegroundColor Gray
Write-Host ""
