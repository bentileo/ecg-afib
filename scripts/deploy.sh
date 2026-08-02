#!/usr/bin/env bash
#
# Deploy the ECG screening dashboard to the VPS.
#
# Run on the server, either by hand or from the GitHub Actions workflow:
#   bash /opt/ecg-afib/scripts/deploy.sh

set -euo pipefail

REPO_PATH="/opt/ecg-afib"
SERVICE_NAME="ecg-afib"
BRANCH="main"

echo "Deploying ${SERVICE_NAME} from ${REPO_PATH}"

# 1. Move into the repository
cd "${REPO_PATH}"

# 2. Fetch the latest code, discarding any local changes on the server
git fetch origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

# 3. Install dependencies to match the lock file
poetry install --only main --no-interaction

# 4. Check the model exists; the dashboard cannot start without it
if [ ! -f models/afib_rf.joblib ]; then
    echo "No model found. Run 'make train' on a machine that has the dataset."
    exit 1
fi

# 5. Restart the service and wait for it to settle
sudo systemctl restart "${SERVICE_NAME}"
sleep 3

# 6. Confirm it came back up
if systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "Deployed. ${SERVICE_NAME} is running."
else
    echo "${SERVICE_NAME} failed to start. Recent logs:"
    sudo journalctl -u "${SERVICE_NAME}" -n 30 --no-pager
    exit 1
fi
