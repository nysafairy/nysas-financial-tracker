# Create and push a version tag to trigger the GitHub "Release builds" workflow.
# Requires: git, and either GitHub CLI (gh) authenticated OR push access to origin.
#
# Usage (from repo root or any folder):
#   .\scripts\create-release.ps1 -Version 0.1.0
#   .\scripts\create-release.ps1 -Version v0.1.0
#   .\scripts\create-release.ps1 -Version 0.1.0 -DryRun
#   .\scripts\create-release.ps1 -Version 0.1.0 -Force   # allow dirty working tree
#
# What it does:
#   1. Normalises the version to vX.Y.Z
#   2. Ensures you are on a branch tracking origin (warns if not)
#   3. Creates an annotated git tag
#   4. Pushes the tag to origin (this starts .github/workflows/release.yml)
#   5. Optionally opens the Actions / Releases page with gh

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Version,

    [switch]$DryRun,
    [switch]$Force,
    [switch]$SkipPush
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $repoRoot

function Resolve-GitExe {
    $cmd = Get-Command git -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) {
        return $cmd.Source
    }
    $candidates = @(
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "C:\Program Files (x86)\Git\cmd\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
    )
    foreach ($path in $candidates) {
        if (Test-Path -LiteralPath $path) {
            $dir = Split-Path -Parent $path
            if ($env:Path -notlike "*$dir*") {
                $env:Path = "$dir;$env:Path"
            }
            return $path
        }
    }
    throw @"
Git was not found on PATH.

Install Git for Windows (https://git-scm.com/download/win), then either:
  - Open a new PowerShell window, or
  - Ensure 'C:\Program Files\Git\cmd' is on your PATH.
"@
}

$Git = Resolve-GitExe
Write-Host "Using git: $Git"

# Normalise to vX.Y.Z
$tag = $Version.Trim()
if ($tag -notmatch '^v') {
    $tag = "v$tag"
}
if ($tag -notmatch '^v\d+\.\d+\.\d+([.-][0-9A-Za-z.-]+)?$') {
    throw "Version must look like 0.1.0 or v0.1.0 (got '$Version')"
}

Write-Host "Repository: $repoRoot"
Write-Host "Release tag: $tag"

$status = & $Git status --porcelain
if ($status -and -not $Force) {
    Write-Host ""
    Write-Host "Working tree has uncommitted changes:" -ForegroundColor Yellow
    & $Git status --short
    throw "Commit or stash changes first, or pass -Force to tag anyway."
}

$existing = & $Git tag -l $tag
if ($existing) {
    throw "Tag '$tag' already exists locally. Delete it first if you intend to recreate: git tag -d $tag"
}

$remoteTags = & $Git ls-remote --tags origin "refs/tags/$tag" 2>$null
if ($remoteTags) {
    throw "Tag '$tag' already exists on origin."
}

$branch = & $Git rev-parse --abbrev-ref HEAD
$sha = & $Git rev-parse --short HEAD
Write-Host "Current branch: $branch @ $sha"

if ($DryRun) {
    Write-Host ""
    Write-Host "[DryRun] Would create annotated tag $tag and push to origin." -ForegroundColor Cyan
    Write-Host "[DryRun] That push triggers workflow: Release builds"
    exit 0
}

$message = "Release $tag"
& $Git tag -a $tag -m $message
if ($LASTEXITCODE -ne 0) { throw "Failed to create tag $tag" }
Write-Host "Created local tag $tag"

if ($SkipPush) {
    Write-Host "Skipped push (-SkipPush). Push later with: git push origin $tag"
    exit 0
}

Write-Host "Pushing tag to origin…"
& $Git push origin $tag
if ($LASTEXITCODE -ne 0) { throw "Failed to push tag $tag to origin" }

Write-Host ""
Write-Host "Tag pushed. GitHub Actions will build Windows / macOS / Linux and publish a Release." -ForegroundColor Green

if (Get-Command gh -ErrorAction SilentlyContinue) {
    try {
        $repo = gh repo view --json url -q .url 2>$null
        if ($repo) {
            Write-Host "Actions:  $repo/actions"
            Write-Host "Releases: $repo/releases"
        }
        Write-Host ""
        Write-Host "Watch the workflow with: gh run watch"
        Write-Host "Or list runs:            gh run list --workflow=`"Release builds`""
    } catch {
        # gh optional beyond this point
    }
} else {
    Write-Host "Install GitHub CLI (gh) if you want quick links: winget install GitHub.cli"
}
