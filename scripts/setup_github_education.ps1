# GitHub Education Deployment Setup Script (PowerShell)
# Romanian Public Procurement Platform

param(
    [string]$DomainName = "",
    [string]$RailwayToken = "",
    [string]$VercelToken = "",
    [string]$VercelOrgId = "",
    [string]$VercelProjectId = "",
    [string]$SentryDsn = "",
    [string]$SlackWebhookUrl = ""
)

# Colors for output
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Blue"
$WHITE = "White"

# Helper functions
function Write-Step {
    param([string]$Message)
    Write-Host "[STEP] $Message" -ForegroundColor $BLUE
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $GREEN
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $RED
}

Write-Host "GitHub Education Deployment Setup" -ForegroundColor $BLUE
Write-Host "====================================" -ForegroundColor $BLUE
Write-Host ""

# Check prerequisites
Write-Step "Checking prerequisites..."

# Check if GitHub CLI is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "GitHub CLI not found. Please install from: https://cli.github.com/"
    Write-Host "After installation, run: gh auth login"
    exit 1
}

# Check if logged in to GitHub
try {
    $null = gh auth status 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Not logged in to GitHub CLI. Please run: gh auth login"
        exit 1
    }
} catch {
    Write-Error "Not logged in to GitHub CLI. Please run: gh auth login"
    exit 1
}

# Check if Node.js is installed
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js not found. Please install Node.js 18+ from: https://nodejs.org/"
    exit 1
}

Write-Success "Prerequisites check passed!"
Write-Host ""

# Get user input if not provided as parameters
Write-Step "Collecting configuration..."

if (-not $DomainName) {
    $DomainName = Read-Host "Enter your domain name (e.g. procurement-platform.me)"
}

if (-not $RailwayToken) {
    $RailwayToken = Read-Host "Enter your Railway token"
}

if (-not $VercelToken) {
    $VercelToken = Read-Host "Enter your Vercel token"
}

if (-not $VercelOrgId) {
    $VercelOrgId = Read-Host "Enter your Vercel Org ID"
}

if (-not $VercelProjectId) {
    $VercelProjectId = Read-Host "Enter your Vercel Project ID"
}

if (-not $SentryDsn) {
    $SentryDsn = Read-Host "Enter your Sentry DSN (optional - press Enter to skip)"
}

if (-not $SlackWebhookUrl) {
    $SlackWebhookUrl = Read-Host "Enter your Slack webhook URL (optional - press Enter to skip)"
}

# Generate API token using .NET crypto
Add-Type -AssemblyName System.Security
$randomBytes = New-Object byte[] 32
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$rng.GetBytes($randomBytes)
$ApiToken = [System.Convert]::ToHexString($randomBytes).ToLower()
$rng.Dispose()

Write-Host ""
Write-Step "Setting up GitHub secrets and variables..."

# Set GitHub secrets
try {
    gh secret set DATABASE_URL --body "postgresql://placeholder-will-update-after-railway"
    gh secret set RAILWAY_TOKEN --body $RailwayToken
    gh secret set VERCEL_TOKEN --body $VercelToken
    gh secret set VERCEL_ORG_ID --body $VercelOrgId
    gh secret set VERCEL_PROJECT_ID --body $VercelProjectId
    gh secret set API_TOKEN --body $ApiToken

    if ($SentryDsn) {
        gh secret set SENTRY_DSN --body $SentryDsn
    }

    if ($SlackWebhookUrl) {
        gh secret set SLACK_WEBHOOK_URL --body $SlackWebhookUrl
    }

    # Set GitHub variables
    gh variable set API_BASE_URL --body "https://api.$DomainName"
    gh variable set FRONTEND_URL --body "https://$DomainName"
    gh variable set DOMAIN_NAME --body $DomainName

    Write-Success "GitHub secrets and variables configured!"
} catch {
    Write-Error "Failed to set GitHub secrets: $_"
    exit 1
}

Write-Host ""

# Install CLI tools
Write-Step "Installing deployment tools..."

# Install Railway CLI
if (-not (Get-Command railway -ErrorAction SilentlyContinue)) {
    try {
        npm install -g @railway/cli
        Write-Success "Railway CLI installed"
    } catch {
        Write-Warning "Failed to install Railway CLI automatically. Please install manually:"
        Write-Host "npm install -g @railway/cli" -ForegroundColor $YELLOW
    }
} else {
    Write-Success "Railway CLI already installed"
}

# Install Vercel CLI
if (-not (Get-Command vercel -ErrorAction SilentlyContinue)) {
    try {
        npm install -g vercel
        Write-Success "Vercel CLI installed"
    } catch {
        Write-Warning "Failed to install Vercel CLI automatically. Please install manually:"
        Write-Host "npm install -g vercel" -ForegroundColor $YELLOW
    }
} else {
    Write-Success "Vercel CLI already installed"
}

Write-Host ""

# Railway setup instructions
Write-Step "Railway setup instructions..."

Write-Host "Please run the following commands to complete Railway setup:" -ForegroundColor $WHITE
Write-Host ""
Write-Host "railway login" -ForegroundColor $BLUE
Write-Host "railway init" -ForegroundColor $BLUE
Write-Host "railway add postgresql" -ForegroundColor $BLUE
Write-Host "railway add redis" -ForegroundColor $BLUE
Write-Host "railway up --detach" -ForegroundColor $BLUE
Write-Host ""
Write-Host "After Railway deployment, get your DATABASE_URL:" -ForegroundColor $WHITE
Write-Host "railway variables" -ForegroundColor $BLUE
Write-Host ""
Write-Host "Then update the GitHub secret:" -ForegroundColor $WHITE
Write-Host "gh secret set DATABASE_URL --body `"your-actual-database-url`"" -ForegroundColor $BLUE
Write-Host ""

# Frontend setup instructions
Write-Step "Frontend setup instructions..."

Write-Host "To deploy the frontend:" -ForegroundColor $WHITE
Write-Host ""
Write-Host "cd frontend" -ForegroundColor $BLUE
Write-Host "vercel login" -ForegroundColor $BLUE
Write-Host "vercel --prod" -ForegroundColor $BLUE
Write-Host ""
Write-Host "Add your custom domain in Vercel dashboard:" -ForegroundColor $WHITE
Write-Host "1. Go to Project Settings > Domains"
Write-Host "2. Add $DomainName"
Write-Host "3. Add www.$DomainName"
Write-Host ""

# DNS Configuration
Write-Step "DNS Configuration needed..."

Write-Host "Configure these DNS records in your Namecheap dashboard:" -ForegroundColor $WHITE
Write-Host ""
Write-Host "1. CNAME record:"
Write-Host "   Host: `@"
Write-Host "   Value: cname.vercel-dns.com"
Write-Host "   TTL: 1800"
Write-Host ""
Write-Host "2. CNAME record:"
Write-Host "   Host: api"
Write-Host "   Value: your-project.railway.app"
Write-Host "   TTL: 1800"
Write-Host ""
Write-Host "3. CNAME record:"
Write-Host "   Host: www"
Write-Host "   Value: cname.vercel-dns.com"
Write-Host "   TTL: 1800"
Write-Host ""

# Generate summary
Write-Step "Setup Summary"

Write-Host ""
Write-Host "GitHub Education Deployment Setup Complete!" -ForegroundColor $GREEN
Write-Host ""
Write-Host "Your configuration:" -ForegroundColor $WHITE
Write-Host "- Domain: $DomainName"
Write-Host "- Frontend: https://$DomainName"
Write-Host "- API: https://api.$DomainName"
Write-Host "- GitHub Secrets: [Check] Configured"
Write-Host "- CLI Tools: [Check] Installed"
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor $WHITE
Write-Host "1. Complete Railway deployment (see instructions above)"
Write-Host "2. Update DATABASE_URL secret with real connection string"
Write-Host "3. Deploy frontend with Vercel"
Write-Host "4. Configure DNS records"
Write-Host "5. Test your deployment"
Write-Host ""
Write-Host "Monitoring and Automation:" -ForegroundColor $WHITE
Write-Host "- GitHub Actions will run CI/CD automatically"
Write-Host "- Data ingestion will run daily at 4:15 AM and 4:45 AM UTC"
Write-Host "- Health monitoring every 15 minutes"
Write-Host "- Database cleanup every Sunday"
Write-Host "- Storage monitoring with alerts"
Write-Host ""
Write-Host "Your platform will be live at: https://$DomainName" -ForegroundColor $GREEN
Write-Host "API documentation at: https://api.$DomainName/docs" -ForegroundColor $GREEN
Write-Host ""
Write-Host "Total monthly cost: $0 (during MVP phase)" -ForegroundColor $GREEN
Write-Host ""
Write-Host "Need help? Check: GITHUB_EDUCATION_DEPLOYMENT.md" -ForegroundColor $YELLOW

Write-Success "Setup script completed!"