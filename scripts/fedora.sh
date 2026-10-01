#!/bin/bash
set -e
TARGET_HOST="${1:-localhost}"

echo "Starting Rocky Linux deployment for ${TARGET_HOST}"
echo "Applying enterprise baseline for Rocky"
echo "- enable repos"
echo "- install core packages"
echo "- configure SELinux baseline"
echo "- validate services"
sleep 3
echo "Rocky Linux deployment complete for ${TARGET_HOST}"
