#!/usr/bin/env bash
#
# Download the PTB-XL dataset from PhysioNet into data/ptbxl/.
#
# Only the 100 Hz recordings are fetched; the 500 Hz set is roughly ten times
# larger and is not needed, because the features measure intervals between
# R-peaks rather than wave boundaries.
#
#   bash scripts/download_data.sh

set -euo pipefail

DATA_DIR="data/ptbxl"
BASE_URL="https://physionet.org/files/ptb-xl/1.0.3"
EXPECTED_RECORDS=21799

echo "Downloading PTB-XL (about 500 MB) into ${DATA_DIR}"

# 1. Make sure wget is available
if ! command -v wget >/dev/null 2>&1; then
    echo "wget is required. Install it with 'brew install wget' or your package manager."
    exit 1
fi

# 2. Create the target directory
mkdir -p "${DATA_DIR}"

# 3. Fetch the metadata and the 100 Hz recordings
#    -c resumes partial downloads, -N skips files already present
wget --recursive --timestamping --continue --no-parent --no-host-directories \
     --cut-dirs=3 --directory-prefix="${DATA_DIR}" \
     --reject "index.html*" \
     "${BASE_URL}/ptbxl_database.csv" \
     "${BASE_URL}/scp_statements.csv" \
     "${BASE_URL}/records100/"

# 4. Confirm every record arrived
FOUND=$(find "${DATA_DIR}/records100" -name "*_lr.dat" | wc -l | tr -d ' ')
echo "Found ${FOUND} of ${EXPECTED_RECORDS} recordings"

if [ "${FOUND}" -lt "${EXPECTED_RECORDS}" ]; then
    echo "Download incomplete. Re-run this script to resume."
    exit 1
fi

echo "Download complete."
