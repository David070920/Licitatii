# 🚀 Deployment Guide - Romanian Procurement Platform

## Overview

This guide covers deploying the Romanian Public Procurement Platform on various cloud providers, with specific focus on **DigitalOcean** and **VPS** deployments.

## 🎯 Deployment Options

### 1. DigitalOcean App Platform (Recommended for Beginners)
- **Cost**: $12-25/month
- **Difficulty**: Easy
- **Features**: Auto-scaling, managed database, SSL certificates
- **Setup Time**: 10-15 minutes

### 2. DigitalOcean Droplets + Docker (Recommended for Control)
- **Cost**: $6-20/month
- **Difficulty**: Medium
- **Features**: Full control, custom configurations
- **Setup Time**: 30-45 minutes

### 3. Any VPS Provider (Hetzner, Linode, Vultr, etc.)
- **Cost**: $4-15/month
- **Difficulty**: Medium
- **Features**: Maximum control, cost-effective
- **Setup Time**: 30-60 minutes

## 🔧 Option 1: DigitalOcean App Platform

### Prerequisites
- DigitalOcean account
- GitHub repository with your code
- Domain name (optional)

### Step 1: Push Code to GitHub
```bash
git add .
git commit -m "Prepare for deployment"
git push origin main
```

### Step 2: Create App on DigitalOcean
1. Go to [DigitalOcean Apps](https://cloud.digitalocean.com/apps)
2. Click "Create App"
3. Connect your GitHub repository
4. Select the branch (usually `main`)
5. Use the provided `deploy/digitalocean-app.yaml` configuration

### Step 3: Configure Environment Variables
In the DigitalOcean dashboard, set these environment variables:

```env
DATABASE_URL=(will be auto-generated)
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
CORS_ORIGINS=["https://your-domain.com"]
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Step 4: Deploy
1. Click "Create Resources"
2. Wait for deployment (5-10 minutes)
3. Your API will be available at: `https://your-app-name.ondigitalocean.app`

### Step 5: Initialize Database
```bash
# Run this once after deployment
curl -X POST "https://your-app-name.ondigitalocean.app/init-db"
```

## 🐳 Option 2: DigitalOcean Droplets with Docker

### Prerequisites
- DigitalOcean account
- Domain name
- Basic Linux knowledge

### Step 1: Create Droplet
1. Create a new Droplet (Ubuntu 22.04)
2. Choose size: $6/month (Basic plan) or higher
3. Add SSH key
4. Enable monitoring and backups (optional)

### Step 2: Connect to Droplet
```bash
ssh root@your-droplet-ip
```

### Step 3: Install Docker
```bash
# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Start Docker
systemctl start docker
systemctl enable docker
```

### Step 4: Deploy Application
```bash
# Clone repository
git clone https://github.com/your-username/romanian-procurement-platform.git
cd romanian-procurement-platform

# Copy production compose file
cp deploy/docker-compose.prod.yml docker-compose.yml

# Create environment file
cat > .env << EOF
DB_PASSWORD=your-secure-database-password
SECRET_KEY=your-super-secret-key-here-make-it-long-and-random
EOF

# Start services
docker-compose up -d
```

### Step 5: Setup SSL with Let's Encrypt
```bash
# Install Certbot
apt install certbot python3-certbot-nginx -y

# Get SSL certificate
certbot certonly --standalone -d your-domain.com

# Copy certificates to nginx directory
mkdir -p deploy/ssl
cp /etc/letsencrypt/live/your-domain.com/fullchain.pem deploy/ssl/
cp /etc/letsencrypt/live/your-domain.com/privkey.pem deploy/ssl/

# Restart nginx
docker-compose restart nginx
```

### Step 6: Initialize Database
```bash
# Run initialization script
docker-compose exec api python init_db.py
```

## 🖥️ Option 3: Any VPS Provider

### For Hetzner, Linode, Vultr, etc.

The process is similar to DigitalOcean Droplets:

1. **Create VPS instance**
2. **Install Docker** (same commands as above)
3. **Deploy application** (same Docker commands)
4. **Setup domain and SSL**

### Specific Provider Notes:

#### Hetzner Cloud
- **Cost**: €3.29/month for CX11
- **Performance**: Excellent price/performance
- **Setup**: Same as DigitalOcean

#### Linode
- **Cost**: $5/month for Nanode
- **Performance**: Good SSD performance
- **Setup**: Same as DigitalOcean

#### Vultr
- **Cost**: $2.50/month for basic plan
- **Performance**: Good global coverage
- **Setup**: Same as DigitalOcean

## 🔐 Security Configuration

### 1. Firewall Setup
```bash
# Ubuntu firewall
ufw allow ssh
ufw allow 80
ufw allow 443
ufw enable

# For Docker
ufw allow 2376/tcp  # Docker daemon
ufw allow 2377/tcp  # Docker swarm
```

### 2. Environment Variables
Never commit these to version control:
```env
DATABASE_URL=postgresql://user:password@host:5432/db
SECRET_KEY=your-secret-key-minimum-32-characters-long
CORS_ORIGINS=["https://your-domain.com"]
```

### 3. Database Security
- Use strong passwords
- Enable SSL connections
- Regular backups
- Monitor connections

## 📊 Monitoring and Logs

### View Application Logs
```bash
# Docker logs
docker-compose logs -f api

# Specific service logs
docker-compose logs -f db
docker-compose logs -f redis
```

### Health Checks
- API Health: `https://your-domain.com/health`
- Database status: Check Docker logs
- Redis status: Check Docker logs

## 🔄 Updates and Maintenance

### Update Application
```bash
# Pull latest code
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Database Backups
```bash
# Backup database
docker-compose exec db pg_dump -U procurement procurement_db > backup.sql

# Restore database
docker-compose exec -T db psql -U procurement procurement_db < backup.sql
```

## 📈 Performance Optimization

### 1. Database Optimization
```bash
# Increase shared_buffers in PostgreSQL
# Add to docker-compose.yml under db environment:
POSTGRES_SHARED_BUFFERS=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=1GB
```

### 2. Redis Configuration
```bash
# Add to docker-compose.yml under redis command:
redis-server --maxmemory 128mb --maxmemory-policy allkeys-lru
```

### 3. Application Scaling
```bash
# Scale API instances
docker-compose up -d --scale api=3
```

## 💰 Cost Breakdown

### DigitalOcean App Platform
- **App**: $12/month
- **Database**: $15/month
- **Total**: ~$27/month

### DigitalOcean Droplets
- **Droplet**: $6/month
- **Database**: $15/month (managed) or $0 (self-hosted)
- **Total**: $6-21/month

### Hetzner Cloud
- **VPS**: €3.29/month
- **Database**: Self-hosted
- **Total**: ~€3.29/month

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Error**
   ```bash
   # Check database logs
   docker-compose logs db
   
   # Verify environment variables
   docker-compose exec api env | grep DATABASE
   ```

2. **SSL Certificate Issues**
   ```bash
   # Renew certificates
   certbot renew
   
   # Check certificate status
   certbot certificates
   ```

3. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Stop conflicting services
   docker-compose down
   ```

## 🎉 Success Verification

After deployment, verify:
- ✅ API responds at `/health`
- ✅ Documentation available at `/api/v1/docs`
- ✅ Database connection works
- ✅ Authentication endpoints work
- ✅ SSL certificate is valid

## 📞 Support

If you encounter issues:
1. Check the logs first
2. Verify environment variables
3. Ensure all services are running
4. Check firewall settings
5. Verify DNS configuration

Your Romanian Public Procurement Platform is now ready for production! 🚀