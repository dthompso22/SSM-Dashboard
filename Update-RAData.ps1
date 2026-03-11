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
    $pkgId = [string]$r['PACKAGE_ID']
    $ras[$pkgId] = [ordered]@{
        pkg_id        = [int]$r['PACKAGE_ID']
        ra_num        = [int]$r['RA_NUM']
        title         = [string]$r['TITLE']
        created       = ([datetime]$r['CREATION_DATE']).ToString("yyyy-MM-dd")
        type          = [string]$r['PACKAGE_TYPE']
        primary_owner = if ($r['PRIMARY_OWNER'] -is [DBNull]) { "" } else { [string]$r['PRIMARY_OWNER'] }
        envs          = [ordered]@{}
        upgrade_ver   = $false
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
    env.SHORT_NAME,
    era.INSTALL_STATUS_C,
    era.INSTALL_DATE,
    era.APPLICABLE_YN,
    era.REQUIRE_W_UPGRD_YN
FROM XPG_ENV_RA_AND_REL era
JOIN SLG_RA_ENVIRONMENT env ON env.ENV_ID = era.ENV_ID
WHERE era.PACKAGE_ID IN ($pkgIdList)
  AND env.CUSTOMER_ID = '618'
  AND era.APPLICABLE_YN = 'Y'
  AND env.SHORT_NAME != 'PRD'
ORDER BY era.PACKAGE_ID, env.SHORT_NAME
"

$r = $cmd.ExecuteReader()
while ($r.Read()) {
    $pkgId = [string]$r['PACKAGE_ID']
    if (-not $ras.Contains($pkgId)) { continue }

    $shortName    = [string]$r['SHORT_NAME']
    $statusC      = if ($r['INSTALL_STATUS_C'] -is [DBNull]) { -1 } else { [int]$r['INSTALL_STATUS_C'] }
    $installDate  = $r['INSTALL_DATE']
    $requireUpgrd = [string]$r['REQUIRE_W_UPGRD_YN']

    # Install status: 3 = Completed, non-null install date = done, 2 = Pending
    if ($statusC -eq 3 -or (-not ($installDate -is [DBNull]))) {
        $ras[$pkgId].envs[$shortName] = "done"
    } elseif ($statusC -eq 2) {
        $ras[$pkgId].envs[$shortName] = "pending"
    }

    # Flag upgrade-required SUs (goes to PRD with upgrade, not standalone)
    if ($requireUpgrd -eq 'Y' -and $ras[$pkgId].type -eq 'Special Update') {
        $ras[$pkgId].upgrade_ver = $true
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

$output | ConvertTo-Json -Depth 5 | Set-Content -Path $OutputFile -Encoding UTF8

Write-Host ""
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host "    Done! $($output.Count) RAs written." -ForegroundColor Green
Write-Host "  ========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Restart the dashboard to load the new data." -ForegroundColor Yellow
Write-Host "  Then commit + push ra_data.json to share with the team." -ForegroundColor Gray
Write-Host ""
