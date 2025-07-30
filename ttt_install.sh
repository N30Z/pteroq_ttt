#!/bin/bash
set -e
apt -y update
apt -y --no-install-recommends install curl ca-certificates
mkdir -p /mnt/server/steamcmd
curl -sSL https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz \
    | tar -xz -C /mnt/server/steamcmd
cd /mnt/server/steamcmd || exit 1
./steamcmd.sh +force_install_dir /mnt/server \
    +login "${STEAM_USER}" "${STEAM_PASS}" "${STEAM_AUTH}" \
    +app_update "${SRCDS_APPID}" validate +quit

