#!/bin/bash
set -e

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BRANCH="${1:-main}"

echo "=== Moonboard Update ==="
echo "Repo: $REPO_DIR"
echo "Branch: $BRANCH"

# Pull latest code
echo ""
echo "Pulling latest changes..."
cd "$REPO_DIR"
git fetch origin "$BRANCH"
git checkout "$BRANCH"
git pull origin "$BRANCH"

# Restart services
echo ""
echo "Restarting services..."
for service in moonboard_ble moonboard_led; do
    if systemctl is-enabled "${service}.service" &>/dev/null; then
        echo "  Restarting ${service}..."
        sudo systemctl restart "${service}.service"
        echo "  ${service}: $(systemctl is-active ${service}.service)"
    else
        echo "  ${service}: not installed, skipping"
    fi
done

echo ""
echo "Update complete."
