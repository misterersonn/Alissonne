#!/usr/bin/env bash
# Installe Blender 4.2 LTS en mode sans écran (rendu logiciel Mesa via Xvfb).
# Usage : bash install_blender.sh   puis   xvfb-run -a blender -b --python script.py
set -euo pipefail
VER=4.2.23
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq xvfb libegl1 libegl-mesa0 libgl1-mesa-dri \
  libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libsm6
mkdir -p /opt/blender
curl -sS https://download.blender.org/release/Blender4.2/blender-${VER}-linux-x64.tar.xz | tar -xJ -C /opt/blender
ln -sf /opt/blender/blender-${VER}-linux-x64/blender /usr/local/bin/blender
blender --version | head -1
