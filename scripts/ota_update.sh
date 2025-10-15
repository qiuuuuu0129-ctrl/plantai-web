#!/usr/bin/env bash
set -e
REPO_DIR=/home/pi/PLANTAI-WEB
cd $REPO_DIR
git pull --rebase
sudo systemctl restart plantai.service || true
echo "[OTA] done at $(date)"
