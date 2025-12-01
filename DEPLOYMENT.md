# DrillBuilder Production Deployment Guide

This guide provides step-by-step instructions for deploying the DrillBuilder application to a production server.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Server Requirements](#server-requirements)
- [Installation Steps](#installation-steps)
- [Database Setup](#database-setup)
- [Environment Configuration](#environment-configuration)
- [WSGI Server Setup (Gunicorn)](#wsgi-server-setup-gunicorn)
- [Nginx Configuration](#nginx-configuration)
- [Systemd Service Setup](#systemd-service-setup)
- [SSL/HTTPS Setup](#sslhttps-setup)
- [Initial Deployment](#initial-deployment)
- [Post-Deployment Tasks](#post-deployment-tasks)
- [Maintenance and Updates](#maintenance-and-updates)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Root or sudo access to the server
- Domain name pointed to your server IP (for SSL)
- Basic command line knowledge

## Server Requirements

### Minimum Specifications
- **CPU**: 1 core (2+ recommended)
- **RAM**: 1GB (2GB+ recommended)
- **Storage**: 10GB available space
- **OS**: Ubuntu 20.04 LTS or newer

### Software Dependencies
- Python 3.9+
- PostgreSQL 12+
- Nginx
- Git (for deployment)

---

## Installation Steps

### 1. Update System Packages

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install System Dependencies

```bash
sudo apt install -y python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib nginx git \
    libpq-dev build-essential supervisor
```

### 3. Create Application User

Create a dedicated user for running the application:

```bash
sudo adduser --system --group --home /opt/drillbuilder drillbuilder
```

### 4. Set Up Application Directory

```bash
sudo mkdir -p /opt/drillbuilder
sudo chown drillbuilder:drillbuilder /opt/drillbuilder
```

### 5. Clone Repository

```bash
sudo -u drillbuilder git clone https://github.com/jeffholland/drillbuilder.git /opt/drillbuilder/app
cd /opt/drillbuilder/app
```

### 6. Create Python Virtual Environment

```bash
sudo -u drillbuilder python3 -m venv /opt/drillbuilder/venv
```

### 7. Install Python Dependencies

```bash
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install --upgrade pip
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install -r /opt/drillbuilder/app/requirements.txt
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install gunicorn psycopg2-binary
```

### 8. Add Pillow for Image Support

```bash
sudo apt install -y libjpeg-dev zlib1g-dev
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install Pillow==12.0.0
```

---

## Database Setup

### 1. Create PostgreSQL Database and User

```bash
sudo -u postgres psql
```

Inside PostgreSQL prompt:

```sql
CREATE DATABASE drillbuilder_prod;
CREATE USER drillbuilder WITH PASSWORD 'your_secure_password_here';
ALTER ROLE drillbuilder SET client_encoding TO 'utf8';
ALTER ROLE drillbuilder SET default_transaction_isolation TO 'read committed';
ALTER ROLE drillbuilder SET timezone TO 'UTC';
GRANT ALL PRIVILEGES ON DATABASE drillbuilder_prod TO drillbuilder;
\q
```

### 2. Test Database Connection

```bash
PGPASSWORD='your_secure_password_here' psql -h localhost -U drillbuilder -d drillbuilder_prod -c "SELECT version();"
```

---

## Environment Configuration

### 1. Create Environment File

```bash
sudo -u drillbuilder nano /opt/drillbuilder/.env
```

Add the following content (replace placeholder values):

```bash
# Flask Configuration
FLASK_APP=drillbuilder.app
FLASK_ENV=production
SECRET_KEY=your_very_long_random_secret_key_here_min_32_chars

# JWT Configuration
JWT_SECRET_KEY=your_very_long_random_jwt_secret_key_here_min_32_chars

# Database Configuration
DATABASE_URL=postgresql://drillbuilder:your_secure_password_here@localhost/drillbuilder_prod

# Application Settings
UPLOAD_FOLDER=/opt/drillbuilder/app/instance/uploads
MAX_CONTENT_LENGTH=5242880
```

### 2. Generate Secure Secret Keys

Use Python to generate secure random keys:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run this twice and use the outputs for `SECRET_KEY` and `JWT_SECRET_KEY`.

### 3. Set Proper Permissions

```bash
sudo chmod 600 /opt/drillbuilder/.env
sudo chown drillbuilder:drillbuilder /opt/drillbuilder/.env
```

### 4. Create Instance and Upload Directories

```bash
sudo -u drillbuilder mkdir -p /opt/drillbuilder/app/instance/uploads
sudo chmod 755 /opt/drillbuilder/app/instance
sudo chmod 755 /opt/drillbuilder/app/instance/uploads
```

---

## WSGI Server Setup (Gunicorn)

### 1. Create Gunicorn Configuration

```bash
sudo -u drillbuilder nano /opt/drillbuilder/gunicorn.conf.py
```

Add the following:

```python
import multiprocessing

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Logging
errorlog = "/opt/drillbuilder/logs/gunicorn-error.log"
accesslog = "/opt/drillbuilder/logs/gunicorn-access.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "drillbuilder"

# Server mechanics
daemon = False
pidfile = "/opt/drillbuilder/gunicorn.pid"
user = "drillbuilder"
group = "drillbuilder"
tmp_upload_dir = None

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

### 2. Create Log Directory

```bash
sudo -u drillbuilder mkdir -p /opt/drillbuilder/logs
```

### 3. Test Gunicorn

```bash
cd /opt/drillbuilder/app
sudo -u drillbuilder /opt/drillbuilder/venv/bin/gunicorn \
    --config /opt/drillbuilder/gunicorn.conf.py \
    --chdir /opt/drillbuilder/app \
    "drillbuilder.app:app"
```

Press `Ctrl+C` to stop after verifying it starts without errors.

---

## Nginx Configuration

### 1. Create Nginx Site Configuration

```bash
sudo nano /etc/nginx/sites-available/drillbuilder
```

Add the following (replace `your-domain.com` with your actual domain):

```nginx
upstream drillbuilder_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 5M;

    access_log /var/log/nginx/drillbuilder-access.log;
    error_log /var/log/nginx/drillbuilder-error.log;

    location /static/ {
        alias /opt/drillbuilder/app/drillbuilder/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /images/serve/ {
        alias /opt/drillbuilder/app/instance/uploads/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://drillbuilder_app;
    }
}
```

### 2. Enable the Site

```bash
sudo ln -s /etc/nginx/sites-available/drillbuilder /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default  # Remove default site if present
```

### 3. Test Nginx Configuration

```bash
sudo nginx -t
```

# edit: if test fails:

```bash
# Create the nginx configuration file
sudo nano /etc/nginx/sites-available/drillbuilder
```

# then paste this config:

```bash
upstream drillbuilder_app {
    server 127.0.0.1:8000 fail_timeout=0;
}

server {
    listen 80;
    listen [::]:80;
    server_name your-domain.com www.your-domain.com;

    client_max_body_size 5M;

    access_log /var/log/nginx/drillbuilder-access.log;
    error_log /var/log/nginx/drillbuilder-error.log;

    location /static/ {
        alias /opt/drillbuilder/app/drillbuilder/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /images/serve/ {
        alias /opt/drillbuilder/app/instance/uploads/;
        expires 30d;
        add_header Cache-Control "public";
    }

    location / {
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Host $http_host;
        proxy_redirect off;
        proxy_buffering off;
        
        proxy_pass http://drillbuilder_app;
    }
}
```

# Save, then:

```bash
# Create the symbolic link
sudo ln -s /etc/nginx/sites-available/drillbuilder /etc/nginx/sites-enabled/drillbuilder

# Test nginx configuration
sudo nginx -t

# If test passes, reload nginx
sudo systemctl reload nginx
```

### 4. Restart Nginx

```bash
sudo systemctl restart nginx
```

---

## Systemd Service Setup

### 1. Create Systemd Service File

```bash
sudo nano /etc/systemd/system/drillbuilder.service
```

Add the following:

```ini
[Unit]
Description=DrillBuilder Web Application
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=drillbuilder
Group=drillbuilder
RuntimeDirectory=drillbuilder
WorkingDirectory=/opt/drillbuilder/app
Environment="PATH=/opt/drillbuilder/venv/bin"
EnvironmentFile=/opt/drillbuilder/.env
ExecStart=/opt/drillbuilder/venv/bin/gunicorn \
    --config /opt/drillbuilder/gunicorn.conf.py \
    --chdir /opt/drillbuilder/app \
    "drillbuilder.app:app"
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 2. Reload Systemd and Enable Service

```bash
sudo systemctl daemon-reload
sudo systemctl enable drillbuilder
```

---

## SSL/HTTPS Setup

### 1. Install Certbot

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 2. Obtain SSL Certificate

```bash
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Follow the prompts to:
- Enter your email address
- Agree to terms of service
- Choose whether to redirect HTTP to HTTPS (recommended: yes)

### 3. Test Auto-Renewal

```bash
sudo certbot renew --dry-run
```

The certificate will auto-renew via a cron job.

---

## Initial Deployment

### 1. Initialize Database

```bash
cd /opt/drillbuilder/app
sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app init-db
```

### 2. Run Database Migrations

```bash
cd /opt/drillbuilder/app
sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db upgrade
```

### 3. Start the Application

```bash
sudo systemctl start drillbuilder
```

### 4. Check Service Status

```bash
sudo systemctl status drillbuilder
```

You should see "active (running)" in green.

### 5. View Logs

```bash
# Application logs
sudo journalctl -u drillbuilder -f

# Gunicorn logs
sudo tail -f /opt/drillbuilder/logs/gunicorn-error.log
sudo tail -f /opt/drillbuilder/logs/gunicorn-access.log

# Nginx logs
sudo tail -f /var/log/nginx/drillbuilder-error.log
sudo tail -f /var/log/nginx/drillbuilder-access.log
```

---

## Post-Deployment Tasks

### 1. Test the Application

Visit your domain in a web browser:
- https://your-domain.com

Test key functionality:
- User registration
- User login
- Create a drill
- Add questions (MCQ, Cloze, Word Match)
- Upload images
- Take a drill
- View results

### 2. Create Initial Admin User (Optional)

If you want to create an admin user via command line:

```bash
cd /opt/drillbuilder/app
sudo -u drillbuilder /opt/drillbuilder/venv/bin/python3 -c "
from drillbuilder.app import app
from drillbuilder.extensions import db
from drillbuilder.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    admin = User(
        username='admin',
        email='admin@your-domain.com',
        password_hash=generate_password_hash('change_this_password')
    )
    db.session.add(admin)
    db.session.commit()
    print('Admin user created successfully')
"
```

### 3. Set Up Monitoring

Consider setting up monitoring tools:
- **Uptime monitoring**: UptimeRobot, Pingdom
- **Log monitoring**: Papertrail, Loggly
- **Server monitoring**: Netdata, Prometheus + Grafana

### 4. Configure Firewall

```bash
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable
```

### 5. Set Up Automated Backups

Create a backup script:

```bash
sudo nano /opt/drillbuilder/backup.sh
```

Add:

```bash
#!/bin/bash
BACKUP_DIR="/opt/drillbuilder/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
PGPASSWORD='your_secure_password_here' pg_dump -h localhost -U drillbuilder drillbuilder_prod > $BACKUP_DIR/db_$DATE.sql

# Backup uploaded images
tar -czf $BACKUP_DIR/uploads_$DATE.tar.gz /opt/drillbuilder/app/instance/uploads/

# Keep only last 30 days of backups
find $BACKUP_DIR -name "db_*.sql" -mtime +30 -delete
find $BACKUP_DIR -name "uploads_*.tar.gz" -mtime +30 -delete
```

Make it executable:

```bash
sudo chmod +x /opt/drillbuilder/backup.sh
sudo chown drillbuilder:drillbuilder /opt/drillbuilder/backup.sh
```

Add to crontab (runs daily at 2 AM):

```bash
sudo crontab -e -u drillbuilder
```

Add:

```
0 2 * * * /opt/drillbuilder/backup.sh
```

---

## Maintenance and Updates

### Deploying Code Updates

1. **Navigate to application directory:**
   ```bash
   cd /opt/drillbuilder/app
   ```

2. **Pull latest code:**
   ```bash
   sudo -u drillbuilder git pull origin main
   ```

3. **Install any new dependencies:**
   ```bash
   sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install -r requirements.txt
   ```

4. **Run database migrations (if any):**
   ```bash
   sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db upgrade
   ```

5. **Restart the application:**
   ```bash
   sudo systemctl restart drillbuilder
   ```

6. **Verify the update:**
   ```bash
   sudo systemctl status drillbuilder
   curl -I https://your-domain.com
   ```

### Database Migrations

When models change:

1. **Create migration:**
   ```bash
   cd /opt/drillbuilder/app
   sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db migrate -m "Description of changes"
   ```

2. **Review migration file:**
   ```bash
   ls -la migrations/versions/
   ```

3. **Apply migration:**
   ```bash
   sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db upgrade
   ```

### Log Rotation

Create log rotation configuration:

```bash
sudo nano /etc/logrotate.d/drillbuilder
```

Add:

```
/opt/drillbuilder/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0640 drillbuilder drillbuilder
    sharedscripts
    postrotate
        systemctl reload drillbuilder > /dev/null 2>&1 || true
    endscript
}
```

---

## Troubleshooting

### Application Won't Start

**Check service status:**
```bash
sudo systemctl status drillbuilder
sudo journalctl -u drillbuilder -n 50
```

**Common issues:**
- Database connection failed: Check DATABASE_URL in .env
- Port already in use: Check if another service is using port 8000
- Permission errors: Verify drillbuilder user owns all necessary files

### 502 Bad Gateway

**Check if Gunicorn is running:**
```bash
sudo systemctl status drillbuilder
ps aux | grep gunicorn
```

**Check Nginx configuration:**
```bash
sudo nginx -t
sudo tail -f /var/log/nginx/drillbuilder-error.log
```

### Database Connection Issues

**Test database connection:**
```bash
sudo -u drillbuilder psql -d drillbuilder_prod
```

**Check PostgreSQL status:**
```bash
sudo systemctl status postgresql
```

### Image Upload Failures

**Check upload directory permissions:**
```bash
ls -la /opt/drillbuilder/app/instance/uploads/
sudo chown -R drillbuilder:drillbuilder /opt/drillbuilder/app/instance/uploads/
sudo chmod 755 /opt/drillbuilder/app/instance/uploads/
```

**Check Pillow installation:**
```bash
/opt/drillbuilder/venv/bin/python3 -c "from PIL import Image; print('Pillow OK')"
```

### High Memory Usage

**Check worker count in Gunicorn:**
Edit `/opt/drillbuilder/gunicorn.conf.py` and reduce workers:
```python
workers = 2  # Reduce if memory constrained
```

Restart:
```bash
sudo systemctl restart drillbuilder
```

### SSL Certificate Issues

**Check certificate status:**
```bash
sudo certbot certificates
```

**Renew manually:**
```bash
sudo certbot renew
sudo systemctl reload nginx
```

### View Real-Time Logs

```bash
# All application logs
sudo journalctl -u drillbuilder -f

# Gunicorn only
sudo tail -f /opt/drillbuilder/logs/gunicorn-error.log

# Nginx only
sudo tail -f /var/log/nginx/drillbuilder-error.log
```

---

## Security Checklist

- [ ] Changed default SECRET_KEY and JWT_SECRET_KEY
- [ ] Set strong database password
- [ ] Configured firewall (ufw)
- [ ] Enabled HTTPS/SSL
- [ ] Set proper file permissions (600 for .env)
- [ ] Disabled debug mode (FLASK_ENV=production)
- [ ] Set up automated backups
- [ ] Configured log rotation
- [ ] Regular security updates: `sudo apt update && sudo apt upgrade`
- [ ] Monitor application logs regularly

---

## Performance Optimization

### Database Indexing

Monitor slow queries and add indexes as needed:

```sql
-- Connect to database
sudo -u postgres psql drillbuilder_prod

-- Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY abs(correlation) DESC;

-- Add indexes for common queries (example)
CREATE INDEX idx_quiz_user ON quiz(user_id);
CREATE INDEX idx_question_quiz ON question_base(quiz_id);
CREATE INDEX idx_attempt_user_quiz ON quiz_attempt(user_id, quiz_id);
```

### Caching (Optional)

For high-traffic deployments, consider adding Redis:

```bash
sudo apt install redis-server
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install Flask-Caching redis
```

### CDN for Static Assets (Optional)

For better performance, serve static files through a CDN like Cloudflare or AWS CloudFront.

---

## Support and Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Gunicorn Documentation**: https://docs.gunicorn.org/
- **Nginx Documentation**: https://nginx.org/en/docs/
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/

---

## Quick Reference Commands

```bash
# Start/Stop/Restart Application
sudo systemctl start drillbuilder
sudo systemctl stop drillbuilder
sudo systemctl restart drillbuilder
sudo systemctl status drillbuilder

# View Logs
sudo journalctl -u drillbuilder -f
sudo tail -f /opt/drillbuilder/logs/gunicorn-error.log

# Nginx
sudo systemctl restart nginx
sudo nginx -t

# Database Backup
sudo -u drillbuilder pg_dump drillbuilder_prod > backup.sql

# Update Application
cd /opt/drillbuilder/app && sudo -u drillbuilder git pull && sudo systemctl restart drillbuilder
```

---

**Deployment Version**: 1.0  
**Last Updated**: November 30, 2025  
**Maintainer**: Jeff Holland
