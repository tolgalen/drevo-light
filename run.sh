#!/usr/bin/env bash
# Drevo Light launcher: creates .venv, installs the dependencies and starts the app.
cd "$(dirname "$0")" || exit 1

# Prefer a stable Python: wheels of hidapi/PySide6 often lag behind the newest release.
pick_python() {
  for p in python3.13 python3.12 python3.11 python3.10 python3; do
    command -v "$p" >/dev/null 2>&1 && { command -v "$p"; return; }
  done
}

install_hint() {
  local id=""
  [ -r /etc/os-release ] && id="$(. /etc/os-release; echo "$ID $ID_LIKE")"
  echo "Building 'hidapi' failed. Install the build dependencies and run ./run.sh again:" >&2
  case "$id" in
    *fedora*|*rhel*) echo "  sudo dnf install libusb1-devel systemd-devel gcc python3-devel" >&2 ;;
    *debian*|*ubuntu*) echo "  sudo apt install libusb-1.0-0-dev libudev-dev gcc python3-dev python3-venv" >&2 ;;
    *arch*) echo "  sudo pacman -S libusb base-devel" >&2 ;;
    *suse*) echo "  sudo zypper install libusb-1_0-devel libudev-devel gcc python3-devel" >&2 ;;
    *) echo "  install the libusb-1.0 and libudev development packages, a C compiler and the Python headers" >&2 ;;
  esac
}

if [ ! -d .venv ]; then
  py="$(pick_python)"
  if [ -z "$py" ]; then
    echo "python3 not found. Install Python 3.10 or newer." >&2
    exit 1
  fi
  "$py" -m venv .venv || { echo "Could not create .venv (on Debian/Ubuntu: sudo apt install python3-venv)." >&2; exit 1; }
fi

if [ ! -f .venv/.deps_v11_ok ]; then
  ver="$(.venv/bin/python -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
  case "$ver" in
    3.15|3.16|3.17|3.18|3.19) echo "Note: Python $ver is very new; if installation fails, install Python 3.12/3.13 and delete .venv." >&2 ;;
  esac
  if ! .venv/bin/pip install -r requirements.txt; then
    install_hint
    exit 1
  fi
  touch .venv/.deps_v11_ok
fi

exec .venv/bin/python drevo_light.py "$@"
