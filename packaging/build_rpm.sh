#!/usr/bin/env bash
# Build RPMs for several Fedora releases with podman: packaging/build_rpm.sh [43 44 45]
# Output: dist/rpm/drevo-light-<ver>-1.fcNN.x86_64.rpm
set -e
cd "$(dirname "$0")/.."
root="$PWD"
ver="$(sed -n 's/^APP_VERSION = "\(.*\)"/\1/p' drevolight/core.py)"
mkdir -p dist/rpm
for rel in "${@:-43 44 45}"; do
  for r in $rel; do
    podman run --rm -v "$root":/src:ro,z -v "$root/dist/rpm":/out:z \
      registry.fedoraproject.org/fedora:$r bash -euxc "
        dnf -y -q install rpm-build gcc python3-devel python3-pip libusb1-devel hidapi-devel systemd-devel binutils
        cp -a /src /work && cd /work && rm -rf dist build .venv
        python3 -m venv .venv && .venv/bin/pip install -q -r requirements.txt pyinstaller
        .venv/bin/pyinstaller packaging/drevo-light.spec --noconfirm
        S=\$HOME/rpmbuild/SOURCES; mkdir -p \$S
        cp -a dist/drevo-light \$S/ && cp LICENSE 70-drevo-tyrfing.rules packaging/drevo-light.desktop \$S/ && cp assets/icon.png \$S/
        rpmbuild -bb --define 'app_version $ver' packaging/rpm/drevo-light.spec
        cp \$HOME/rpmbuild/RPMS/x86_64/*.rpm /out/"
  done
done
ls -l dist/rpm
