# 1. Navigate to app directory
cd /opt/drillbuilder/app

# 2. Pull latest code
sudo -u drillbuilder git fetch
sudo -u drillbuilder git pull origin main

# 3. Install any new Python dependencies
sudo -u drillbuilder /opt/drillbuilder/venv/bin/pip install -r requirements.txt

# 4. Run database migrations (if models changed)
sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db upgrade

# 5. Update static file permissions (if new static files added)
sudo chown -R drillbuilder:www-data /opt/drillbuilder/app/drillbuilder/static/
sudo chmod -R 755 /opt/drillbuilder/app/drillbuilder/static/

# 6. Restart the application
sudo systemctl restart drillbuilder

# 7. Verify it's running
sudo systemctl status drillbuilder

# 8. Check for errors
sudo tail -30 /opt/drillbuilder/logs/gunicorn-error.log

# =============================

# When You DON'T Need Migrations

For most code changes (routes, templates, validation logic), you only need:

cd /opt/drillbuilder/app
sudo -u drillbuilder git pull
sudo systemctl restart drillbuilder

# When You DO Need Migrations

Run migrations if you changed database models (added/removed columns, tables, relationships):

sudo -u drillbuilder /opt/drillbuilder/venv/bin/flask --app drillbuilder.app db upgrade

# Quick One-Liner for Simple Updates

cd /opt/drillbuilder/app && sudo -u drillbuilder git pull && sudo systemctl restart drillbuilder && sudo systemctl status drillbuilder