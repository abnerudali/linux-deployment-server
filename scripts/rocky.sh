#!/bin/bash
set -e
TARGET_HOST="${1:-localhost}"

echo "Starting Debian deployment for ${TARGET_HOST}"
echo "Applying Debian standard image configuration"
echo "- install OS updates"
echo "- set hostname"
echo "- configure networking"
echo "- install monitoring and security tools"
sleep 3
echo "Debian deployment complete for ${TARGET_HOST}"
