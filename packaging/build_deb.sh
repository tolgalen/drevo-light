#!/usr/bin/env bash
# Build .deb packages with podman: packaging/build_deb.sh [debian:12 debian:13 ubuntu:22.04 ...]
# Output: dist/deb/drevo-light_<ver>_<distro><rel>_amd64.deb
set -e
cd "$(dirname "$0")/.."
root="$PWD"
ver="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' drevolight/core.py)"
mkdir -p dist/deb
imgs=("$@"); [ ${#imgs[@]} -gt 0 ] || imgs=(debian:12 debian:13 ubuntu:22.04 ubuntu:24.04 ubuntu:26.04)
for img in "${imgs[@]}"; do
  podman run --rm -e DEBIAN_FRONTEND=noninteractive -e IMG="$img" -e VER="$ver" \
    -v "$root":/src:ro,z -v "$root/dist/deb":/out:z docker.io/library/$img bash -euxc '
      apt-get update -qq
      apt-get install -y -qq gcc python3-dev python3-venv python3-pip libusb-1.0-0-dev libhidapi-dev libudev-dev binutils dpkg-dev libegl1 libgl1 libxkbcommon0 libxkbcommon-x11-0 libdbus-1-3 libfontconfig1 libxcb-cursor0 libglib2.0-0 || apt-get install -y -qq libglib2.0-0t64
      cp -a /src /work && cd /work && rm -rf dist build .venv
      python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt pyinstaller
      .venv/bin/pyinstaller packaging/drevo-light.spec --noconfirm
      P=/pkg; D=$P/usr/lib/drevo-light
      mkdir -p $D $P/usr/bin $P/DEBIAN $P/usr/lib/udev/rules.d $P/usr/share/applications $P/usr/share/icons/hicolor/256x256/apps $P/usr/share/doc/drevo-light
      cp -a dist/drevo-light/. $D/
      ln -s ../lib/drevo-light/drevo-light $P/usr/bin/drevo-light
      install -m644 70-drevo-tyrfing.rules $P/usr/lib/udev/rules.d/
      install -m644 assets/icon.png $P/usr/share/icons/hicolor/256x256/apps/drevo-light.png
      sed "s#^Exec=.*#Exec=drevo-light#" packaging/drevo-light.desktop > $P/usr/share/applications/drevo-light.desktop
      install -m644 LICENSE $P/usr/share/doc/drevo-light/copyright
      SIZE=$(du -sk $P | cut -f1)
      cat > $P/DEBIAN/control <<CTL
Package: drevo-light
Version: $VER
Section: utils
Priority: optional
Architecture: amd64
Maintainer: candion <candion@gmail.com>
Installed-Size: $SIZE
Depends: libc6, libegl1, libgl1, libxkbcommon0, libxkbcommon-x11-0, libdbus-1-3, libfontconfig1, libglib2.0-0t64 | libglib2.0-0, libxcb-cursor0, udev
Homepage: https://github.com/tolgalen/drevo-light
Description: Lighting editor for the Drevo Tyrfing V2 keyboard
 Paints keys, manages profiles and starts the built-in effects without the
 official software. Self-contained build (bundles Python and Qt).
CTL
      printf "#!/bin/sh\nudevadm control --reload >/dev/null 2>&1 || true\nudevadm trigger --subsystem-match=hidraw --subsystem-match=usb >/dev/null 2>&1 || true\n" > $P/DEBIAN/postinst
      chmod 755 $P/DEBIAN/postinst
      NAME=$(echo "$IMG" | tr -d ":" )
      dpkg-deb --root-owner-group -Zxz -b $P /out/drevo-light_${VER}_${NAME}_amd64.deb
      apt-get install -y -qq /out/drevo-light_${VER}_${NAME}_amd64.deb
      QT_QPA_PLATFORM=offscreen timeout 8 drevo-light 2>&1 | tail -3 || true; echo "smoke done"'
done
ls -l dist/deb
