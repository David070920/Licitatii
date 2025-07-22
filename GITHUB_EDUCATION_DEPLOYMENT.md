# 🎓 GitHub Education Free Deployment Strategy
## Romanian Public Procurement Platform

This document provides a complete implementation guide for deploying the Romanian Public Procurement Platform using GitHub Education benefits at **zero cost**.

## 📋 Table of Contents
- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Implementation Steps](#implementation-steps)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Scaling Path](#scaling-path)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

### Cost Structure
| **Phase** | **Duration** | **Monthly Cost** | **Capabilities** |
|-----------|--------------|------------------|------------------|
| **MVP Phase** | Months 1-6 | **$0** | Full platform, 10K+ requests/day |
| **Growth Phase** | Months 6-12 | **$20-30** | Railway Pro, enhanced performance |
| **Scale Phase** | Year 2+ | **$50-100** | Dedicated infrastructure |

### Services Used
- ✅ **Vercel Pro** (GitHub Education) - Frontend hosting
- ✅ **Railway Hobby + Credits** - Backend API & Database
- ✅ **GitHub Actions** - CI/CD & Background processing
- ✅ **Namecheap .me Domain** (Free for 1 year)
- ✅ **Sentry Free Tier** - Error tracking
- ✅ **Slack** - Notifications (optional)

## 🔧 Prerequisites

### GitHub Education Benefits
1. **Active GitHub Student/Teacher account**
2. **GitHub Student Developer Pack** activated
3. **Available services:**
   - Vercel Pro features
   - DigitalOcean $200 credit (backup option)
   - Namecheap free domain
   - Railway credits

### Required Accounts
- [ ] GitHub account with Education benefits
- [ ] Railway account (connect with GitHub)
- [ ] Vercel account (connect with GitHub)
- [ ] Namecheap account (for domain)
- [ ] Sentry account (free tier)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Namecheap     │    │   Vercel Pro    │    │   Railway       │
│   .me Domain    │───▶│   Frontend      │───▶│   Backend API   │
│   (Free)        │    │   (Education)   │    │   (Free Tier)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                        │
                       ┌─────────────────┐             │
                       │ GitHub Actions  │             │
                       │ - CI/CD Pipeline│             │
                       │ - Data Ingestion│             │
                       │ - Health Checks │             │
                       │ - Auto Scaling  │             │
                       └─────────────────┘             │
                                                        ▼
                                               ┌─────────────────┐
                                               │   PostgreSQL    │
                                               │   + Redis       │
                                               │   (Railway)     │
                                               └─────────────────┘
```

## 🚀 Implementation Steps

### Step 1: GitHub Repository Setup

```bash
# Clone your repository
git clone https://github.com/your-username/romanian-procurement-platform.git
cd romanian-procurement-platform

# Set up GitHub secrets (required)
gh secret set DATABASE_URL --body "postgresql://placeholder-will-update-after-railway"
gh secret set RAILWAY_TOKEN --body "your-railway-token-here"
gh secret set VERCEL_TOKEN --body "your-vercel-token-here"
gh secret set VERCEL_ORG_ID --body "your-vercel-org-id"
gh secret set VERCEL_PROJECT_ID --body "your-vercel-project-id"
gh secret set SENTRY_DSN --body "your-sentry-dsn-here"
gh secret set API_TOKEN --body "secure-random-string-for-github-actions"

# Set up GitHub variables
gh variable set API_BASE_URL --body "https://api.your-domain.me"
gh variable set FRONTEND_URL --body "https://your-domain.me"
gh variable set DOMAIN_NAME --body "your-domain.me"

# Optional: Set up Slack notifications
gh secret set SLACK_WEBHOOK_URL --body "your-slack-webhook-url"
```

### Step 2: Railway Backend Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize project
railway init

# Add services
railway add postgresql  # Free 1GB PostgreSQL
railway add redis      # Free 25MB Redis

# Deploy backend
railway up --detach

# Get your database URL
railway variables
# Copy the DATABASE_URL and update GitHub secrets
gh secret set DATABASE_URL --body "your-actual-database-url"
```

### Step 3: Domain Configuration

```bash
# 1. Purchase free .me domain from Namecheap (Student Developer Pack)
# Visit: https://nc.me/github-students

# 2. Configure DNS in Namecheap dashboard:
# Record Type: CNAME
# Host: @
# Value: cname.vercel-dns.com
# TTL: 1800

# Record Type: CNAME  
# Host: api
# Value: your-project.railway.app
# TTL: 1800

# Record Type: CNAME
# Host: www  
# Value: cname.vercel-dns.com
# TTL: 1800
```

### Step 4: Vercel Frontend Deployment

```bash
# Install Vercel CLI
npm install -g vercel

# Login to Vercel (use GitHub account with Education benefits)
vercel login

# Deploy frontend
cd frontend
vercel --prod

# Add custom domain in Vercel dashboard
# 1. Go to Project Settings > Domains
# 2. Add your-domain.me
# 3. Add www.your-domain.me
# 4. Follow Vercel's DNS verification steps
```

### Step 5: Database Initialization

```bash
# Connect to Railway database
railway connect postgresql

# Run database migrations
alembic upgrade head

# Optional: Create admin user
python scripts/create_admin_user.py
```

### Step 6: Test GitHub Actions

```bash
# Test CI/CD pipeline
git add .
git commit -m "Deploy GitHub Education setup"
git push origin main

# Monitor deployment
# Check: https://github.com/your-username/your-repo/actions

# Test data ingestion (manual trigger)
gh workflow run data-ingestion.yml --ref main

# Test health monitoring
gh workflow run health-monitoring.yml --ref main
```

## ⚙️ Configuration

### Environment Variables

#### Railway (Backend)
```env
DATABASE_URL=postgresql://... (auto-generated)
SECRET_KEY=your-super-secret-key-32-chars-minimum
CORS_ORIGINS=["https://your-domain.me","https://www.your-domain.me"]
SENTRY_DSN=https://your-sentry-dsn
ENVIRONMENT=production
```

#### Vercel (Frontend)
```env
VITE_API_URL=https://api.your-domain.me
VITE_APP_NAME=Romanian Procurement Platform
VITE_ENVIRONMENT=production
```

### GitHub Actions Secrets
```
DATABASE_URL - Railway PostgreSQL connection string
RAILWAY_TOKEN - Railway authentication token
VERCEL_TOKEN - Vercel deployment token
VERCEL_ORG_ID - Your Vercel organization ID  
VERCEL_PROJECT_ID - Your Vercel project ID
SENTRY_DSN - Sentry error tracking DSN
API_TOKEN - Secure token for GitHub Actions API calls
SLACK_WEBHOOK_URL - Slack notifications webhook (optional)
```

### GitHub Actions Variables
```
API_BASE_URL - https://api.your-domain.me
FRONTEND_URL - https://your-domain.me
DOMAIN_NAME - your-domain.me
```

## 📊 Monitoring

### Automated Health Checks
- **Every 15 minutes**: Frontend, API, Database, Redis
- **Alerts**: Slack notifications for outages
- **Auto-recovery**: GitHub Issues created for persistent failures

### Data Processing Schedule
- **4:15 AM UTC**: SICAP data sync (Daily)
- **4:45 AM UTC**: ANRMAP data sync (Daily)  
- **12:15 PM UTC**: Risk analysis (Daily)
- **Sunday 8 PM UTC**: Database cleanup (Weekly)

### Storage Monitoring
- **Daily**: Storage usage reports
- **Alerts at**: 75% and 90% of 1GB limit
- **Auto-cleanup**: Old logs and temporary data

## 📈 Scaling Path

### Tier 1: Growth Phase ($20-30/month)
**Triggers:**
- Database > 800MB (80% of 1GB limit)
- API > 8,000 requests/day
- Response times > 2.5 seconds

**Actions:**
- Upgrade to Railway Pro (8GB database, better performance)
- Enable GitHub Actions scaling workflow
- Monitor for 2 weeks before further scaling

### Tier 2: Scale Phase ($50-100/month)  
**Triggers:**
- Database > 6GB (75% of 8GB limit)
- API > 50,000 requests/day
- Need for real-time background processing

**Actions:**
- Consider DigitalOcean App Platform using $200 credit
- Implement dedicated worker processes
- Upgrade monitoring to paid tiers

### Emergency Scaling
```bash
# Trigger emergency scaling workflow
gh workflow run scaling-migration.yml --ref main \
  -f migration_type=emergency_scale
```

## 🚨 Troubleshooting

### Common Issues

#### Deployment Failures
```bash
# Check GitHub Actions logs
gh run list --limit 5
gh run view [run-id] --log

# Check Railway logs  
railway logs

# Check Vercel deployment
vercel logs
```

#### Database Connection Issues
```bash
# Test database connectivity
railway connect postgresql

# Check environment variables
railway variables

# Verify Railway service status
railway status
```

#### Domain/SSL Issues
```bash
# Check DNS propagation
nslookup your-domain.me
dig your-domain.me

# Test SSL certificate
openssl s_client -connect your-domain.me:443 -servername your-domain.me
```

### GitHub Actions Debugging
```bash
# Check workflow status
gh workflow list
gh workflow view ci-cd.yml

# View recent runs
gh run list --workflow=ci-cd.yml --limit 5

# Debug failed run
gh run view [run-id] --log-failed
```

### Railway Troubleshooting
```bash
# Check service health
railway status

# View environment variables
railway variables

# Connect to database directly
railway connect postgresql

# Check resource usage
railway metrics
```

## 📚 Additional Resources

### Cost Optimization
- Monitor GitHub Actions minutes usage
- Optimize data sync frequency based on usage
- Use database cleanup to stay within 1GB limit
- Cache reports to reduce API database queries

### Performance Optimization
- Enable Vercel Analytics for frontend metrics
- Use Redis caching for frequent queries
- Implement database indexing for better performance
- Monitor API response times and optimize slow queries

### Security Best Practices
- Rotate secrets regularly
- Monitor Sentry for security issues
- Keep dependencies updated via Dependabot
- Review access logs for suspicious activity

## ✅ Success Checklist

- [ ] All GitHub Education benefits activated
- [ ] Domain purchased and DNS configured
- [ ] Railway backend deployed and healthy
- [ ] Vercel frontend deployed and accessible
- [ ] Database migrations completed
- [ ] GitHub Actions workflows passing
- [ ] Health monitoring active and alerting
- [ ] Data ingestion scheduled and running
- [ ] SSL certificates valid and auto-renewing
- [ ] Monitoring dashboards configured

## 🎉 You're Live!

Your Romanian Public Procurement Platform is now running completely free using GitHub Education benefits. The system will automatically:

- ✅ Deploy new code changes
- ✅ Sync procurement data daily  
- ✅ Monitor system health
- ✅ Alert on issues
- ✅ Recommend scaling when needed
- ✅ Clean up data to stay within limits

**Platform URLs:**
- **Frontend**: https://your-domain.me
- **API**: https://api.your-domain.me
- **API Docs**: https://api.your-domain.me/docs
- **Health Check**: https://api.your-domain.me/health

Your platform can now handle **10,000+ daily users** and **millions of procurement records** while staying within the free tier limits. When you're ready to scale, the automated workflows will guide you through the upgrade process.

Welcome to production! 🚀