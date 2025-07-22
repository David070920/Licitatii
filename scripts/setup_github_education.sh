#!/bin/bash

# 🎓 GitHub Education Deployment Setup Script
# Romanian Public Procurement Platform

set -e  # Exit on any error

echo "🎓 GitHub Education Deployment Setup"
echo "===================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_step "Checking prerequisites..."

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    print_error "GitHub CLI not found. Please install: https://cli.github.com/"
    exit 1
fi

# Check if logged in to GitHub
if ! gh auth status &> /dev/null; then
    print_error "Not logged in to GitHub CLI. Please run: gh auth login"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install Node.js 18+ from: https://nodejs.org/"
    exit 1
fi

print_success "Prerequisites check passed!"
echo ""

# Get user input
print_step "Collecting configuration..."

read -p "Enter your domain name (e.g., procurement-platform.me): " DOMAIN_NAME
read -p "Enter your Railway token: " RAILWAY_TOKEN
read -p "Enter your Vercel token: " VERCEL_TOKEN
read -p "Enter your Vercel Org ID: " VERCEL_ORG_ID
read -p "Enter your Vercel Project ID: " VERCEL_PROJECT_ID
read -p "Enter your Sentry DSN (optional): " SENTRY_DSN
read -p "Enter your Slack webhook URL (optional): " SLACK_WEBHOOK_URL

# Generate API token
API_TOKEN=$(openssl rand -hex 32)

echo ""
print_step "Setting up GitHub secrets and variables..."

# Set GitHub secrets
gh secret set DATABASE_URL --body "postgresql://placeholder-will-update-after-railway"
gh secret set RAILWAY_TOKEN --body "$RAILWAY_TOKEN"
gh secret set VERCEL_TOKEN --body "$VERCEL_TOKEN" 
gh secret set VERCEL_ORG_ID --body "$VERCEL_ORG_ID"
gh secret set VERCEL_PROJECT_ID --body "$VERCEL_PROJECT_ID"
gh secret set API_TOKEN --body "$API_TOKEN"

if [ -n "$SENTRY_DSN" ]; then
    gh secret set SENTRY_DSN --body "$SENTRY_DSN"
fi

if [ -n "$SLACK_WEBHOOK_URL" ]; then
    gh secret set SLACK_WEBHOOK_URL --body "$SLACK_WEBHOOK_URL"
fi

# Set GitHub variables
gh variable set API_BASE_URL --body "https://api.$DOMAIN_NAME"
gh variable set FRONTEND_URL --body "https://$DOMAIN_NAME"
gh variable set DOMAIN_NAME --body "$DOMAIN_NAME"

print_success "GitHub secrets and variables configured!"
echo ""

# Install CLI tools
print_step "Installing deployment tools..."

# Install Railway CLI
if ! command -v railway &> /dev/null; then
    npm install -g @railway/cli
    print_success "Railway CLI installed"
else
    print_success "Railway CLI already installed"
fi

# Install Vercel CLI  
if ! command -v vercel &> /dev/null; then
    npm install -g vercel
    print_success "Vercel CLI installed"
else
    print_success "Vercel CLI already installed"
fi

echo ""

# Railway setup
print_step "Setting up Railway project..."

echo "Please run the following commands to complete Railway setup:"
echo ""
echo -e "${BLUE}railway login${NC}"
echo -e "${BLUE}railway init${NC}"
echo -e "${BLUE}railway add postgresql${NC}"
echo -e "${BLUE}railway add redis${NC}"
echo -e "${BLUE}railway up --detach${NC}"
echo ""
echo "After Railway deployment, get your DATABASE_URL:"
echo -e "${BLUE}railway variables${NC}"
echo ""
echo "Then update the GitHub secret:"
echo -e "${BLUE}gh secret set DATABASE_URL --body \"your-actual-database-url\"${NC}"
echo ""

# Frontend setup
print_step "Frontend setup instructions..."

echo "To deploy the frontend:"
echo ""
echo -e "${BLUE}cd frontend${NC}"
echo -e "${BLUE}vercel login${NC}"
echo -e "${BLUE}vercel --prod${NC}"
echo ""
echo "Add your custom domain in Vercel dashboard:"
echo "1. Go to Project Settings > Domains"
echo "2. Add $DOMAIN_NAME"
echo "3. Add www.$DOMAIN_NAME"
echo ""

# DNS Configuration
print_step "DNS Configuration needed..."

echo "Configure these DNS records in your Namecheap dashboard:"
echo ""
echo "1. CNAME record:"
echo "   Host: @"
echo "   Value: cname.vercel-dns.com"
echo "   TTL: 1800"
echo ""
echo "2. CNAME record:"
echo "   Host: api"  
echo "   Value: your-project.railway.app"
echo "   TTL: 1800"
echo ""
echo "3. CNAME record:"
echo "   Host: www"
echo "   Value: cname.vercel-dns.com"
echo "   TTL: 1800"
echo ""

# Generate summary
print_step "Setup Summary"

cat << EOF

🎉 GitHub Education Deployment Setup Complete!

Your configuration:
- Domain: $DOMAIN_NAME
- Frontend: https://$DOMAIN_NAME
- API: https://api.$DOMAIN_NAME
- GitHub Secrets: ✅ Configured
- CLI Tools: ✅ Installed

Next Steps:
1. Complete Railway deployment (see instructions above)
2. Update DATABASE_URL secret with real connection string
3. Deploy frontend with Vercel
4. Configure DNS records
5. Test your deployment

Monitoring & Automation:
- GitHub Actions will run CI/CD automatically
- Data ingestion will run daily at 4:15 AM & 4:45 AM UTC  
- Health monitoring every 15 minutes
- Database cleanup every Sunday
- Storage monitoring with alerts

Your platform will be live at: https://$DOMAIN_NAME
API documentation at: https://api.$DOMAIN_NAME/docs

Total monthly cost: \$0 (during MVP phase)

Need help? Check: GITHUB_EDUCATION_DEPLOYMENT.md
EOF

print_success "Setup script completed! 🚀"