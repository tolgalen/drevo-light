#!/usr/bin/env bash
# Install Drevo Light for the current user: menu entry, icon and (with sudo) the udev rule.
# Works from the source folder (./run.sh) or from the PyInstaller folder (dist/drevo-light).
set -e
here="$(cd "$(dirname "$0")/.." && pwd)"
if [ -x "$here/drevo-light" ]; then exec_cmd="$here/drevo-light"; else exec_cmd="$here/run.sh"; fi
icon_dir="$HOME/.local/share/icons/hicolor/256x256/apps"
app_dir="$HOME/.local/share/applications"
mkdir -p "$icon_dir" "$app_dir"
cp "$here/assets/icon.png" "$icon_dir/drevo-light.png"
esc_exec="$(printf '%s' "$exec_cmd" | sed 's/[#&\\]/\\&/g')"
sed "s#@EXEC@#$esc_exec#" "$here/packaging/drevo-light.desktop" > "$app_dir/drevo-light.desktop"
echo "Menu entry installed ($app_dir/drevo-light.desktop)"
if [ "${1:-}" != "--no-udev" ]; then
  sudo install -o root -g root -m 644 "$here/99-drevo-tyrfing.rules" /etc/udev/rules.d/99-drevo-tyrfing.rules
  sudo udevadm control --reload && sudo udevadm trigger
  echo "udev rule installed: unplug and plug the keyboard again"
fi
