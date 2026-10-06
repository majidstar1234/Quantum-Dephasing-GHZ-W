$ErrorActionPreference = 'Stop'

Write-Host '=== AI BOOK FACTORY / GITHUB BOOTSTRAP ===' -ForegroundColor Cyan

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw 'GitHub CLI (gh) is not installed. Install it once, then run this script again.'
}

$auth = gh auth status 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host 'GitHub authentication is required.' -ForegroundColor Yellow
    gh auth login
}

$repo = Read-Host 'GitHub repository name (example: my-automated-book)'
if ([string]::IsNullOrWhiteSpace($repo)) {
    throw 'Repository name cannot be empty.'
}

$visibility = Read-Host 'Visibility: private or public [private]'
if ([string]::IsNullOrWhiteSpace($visibility)) { $visibility = 'private' }
if ($visibility -notin @('private','public')) { throw 'Visibility must be private or public.' }

if (-not (Test-Path '.git')) {
    git init
}

git add .
if ((git diff --cached --quiet) -ne $true) {
    git config user.name 'AI Book Factory Bootstrap'
    git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
    git commit -m 'bootstrap: AI Book Factory'
}

$owner = (gh api user --jq .login).Trim()
$full = "$owner/$repo"

$exists = gh repo view $full 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Repository already exists: $full" -ForegroundColor Yellow
    if (-not (git remote get-url origin 2>$null)) {
        git remote add origin "https://github.com/$full.git"
    }
    git branch -M main
    git push -u origin main
} else {
    gh repo create $repo --$visibility --source . --remote origin --push --description 'Autonomous AI Book Factory using GitHub Actions, Gemini and XeLaTeX'
}

Write-Host ''
Write-Host 'Repository published.' -ForegroundColor Green
Write-Host "https://github.com/$full"
Write-Host ''
Write-Host 'NEXT: add GEMINI_API_KEY under Settings > Secrets and variables > Actions.' -ForegroundColor Yellow
Write-Host 'Then run Actions > AI Book Factory - Autonomous > Run workflow.' -ForegroundColor Yellow
