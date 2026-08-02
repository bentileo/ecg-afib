#!/usr/bin/env bash
#
# Deploy the ECG screening dashboard to the VPS.
#
# Run on the server, by hand or from the GitHub Actions workflow:
#   bash /opt/ecg-afib/scripts/deploy.sh
#
# The service restart is permitted without a password by a rule in
# /etc/sudoers.d/ecg-afib, so this runs unattended.

set -euo pipefail

REPO_PATH="/opt/ecg-afib"
SERVICE_NAME="ecg-afib"
BRANCH="main"

echo "Deploying ${SERVICE_NAME} from ${REPO_PATH}"

# 1. Move into the repository
cd "${REPO_PATH}"

# 2. Fetch the latest code, discarding local changes and accepting a rewritten
#    history on the remote
git fetch origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

# 3. Install dependencies to match the lock file
poetry install --only main --no-interaction

# 4. Check the model exists; the dashboard cannot start without it
if [ ! -f models/afib_rf.joblib ]; then
    echo "No model found at ${REPO_PATH}/models/afib_rf.joblib."
    echo "Copy it from a machine that has the dataset:"
    echo "  scp models/afib_rf.joblib ${USER}@\$(hostname -I | awk '{print \$1}'):${REPO_PATH}/models/"
    exit 1
fi

# 5. Restart, and stop here if the restart itself fails. Checking only whether
#    the service is active afterwards is not enough: a failed restart leaves the
#    OLD process running, which looks identical to success.
RESTARTED_AT=$(date +%s)
if ! sudo systemctl restart "${SERVICE_NAME}"; then
    echo "Restart command failed. The previous version may still be running."
    exit 1
fi

# 6. Give it a moment, then confirm it is both running and freshly started
sleep 3

if ! systemctl is-active --quiet "${SERVICE_NAME}"; then
    echo "${SERVICE_NAME} is not running. Recent logs:"
    sudo journalctl -u "${SERVICE_NAME}" -n 30 --no-pager
    exit 1
fi

# A start time older than the restart means the process never actually cycled.
STARTED_AT=$(date -d "$(systemctl show -p ActiveEnterTimestamp --value "${SERVICE_NAME}")" +%s 2>/dev/null || echo 0)
if [ "${STARTED_AT}" -lt "${RESTARTED_AT}" ]; then
    echo "${SERVICE_NAME} did not restart; it is still running the previous version."
    exit 1
fi

echo "Deployed. https://ecg.bentileo.tech"
