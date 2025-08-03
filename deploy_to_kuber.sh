#!/bin/bash
# deploy_to_kuber.sh

REMOTE_USER="root"
REMOTE_HOST="optionniti.com"
REMOTE_PROJECT_DIR="/opt/kuber"
REMOTE_VENV_DIR="/opt/kuber/env"
SERVICE="gunicorn"

# ───────────────────────────────────────────────
echo "📁 Step 1: Pushing changes to GitHub..."

git status
git add .

echo "📝 Enter commit message:"
read COMMIT_MSG
git commit -m "$COMMIT_MSG"
git push origin main || { echo "❌ Push failed. Aborting."; exit 1; }

# ───────────────────────────────────────────────
echo "🚀 Step 2: Deploying on server $REMOTE_HOST..."

ssh ${REMOTE_USER}@${REMOTE_HOST} << EOF
  echo "🔁 Pulling latest changes on server..."
  cd ${REMOTE_PROJECT_DIR} || exit 1
  git pull origin main

  echo "📦 Activating virtualenv and applying migrations..."
  source ${REMOTE_VENV_DIR}/bin/activate

  python manage.py migrate --noinput
  python manage.py collectstatic --noinput

  echo "♻️ Restarting services..."
  sudo systemctl restart ${SERVICE}
  sudo systemctl restart nginx

  echo "✅ Deployment on server complete!"
EOF
