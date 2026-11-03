# Drevo Light

Lighting editor for the **Drevo Tyrfing V2** keyboard (USB `0416:a0f8`), written in Python with PySide6. Runs on Linux and Windows without the official software.

> Status: the protocol has been verified byte for byte against the reference library `dtv2` using a simulated HID device, but it has **not yet been tested with a physical keyboard**.

## Features

- Realistic visual keyboard for selecting keys (click, area drag, Ctrl toggles, Shift replaces) and painting them.
- US ANSI and UK/ES/DE/FR/IT ISO layouts, in full-size and TKL versions.
- Color tab (per key, groups and rows, gradients, recent colors), keyboard effects (static, breathing, radar, stream, ...) and live apply.
- Undo/redo (up to 100 steps) and copy/paste color.
- 20 profiles (colors, effect, mode and layout) with validated JSON import/export.
- 6 languages (es, en, fr, it, de, pt) and 5 themes (system, light, dark, dark blue, Drevo).
- Built-in user manual, printable and exportable to PDF.
- Hardware commands are sent in the background (the UI never blocks); the active profile is re-applied when the keyboard is reconnected.

## Requirements and running

Python 3.10 or newer.

```bash
./run.sh               # Linux/macOS: creates .venv, installs dependencies and starts the app
run.bat                # Windows
python -m drevolight   # if the dependencies are already installed
```

On Linux a udev rule is needed to access the device: menu *File -> Install udev rules* (uses `pkexec`) or `packaging/install_linux.sh`. The rule uses `TAG+="uaccess"`, i.e. access only for the logged-in local user.

## Architecture

```
drevo_light.py         launcher
drevolight/
  app.py               main(): QApplication, splash, window
  window.py            MainWindow: menus, pages, profiles, connection
  keyboard_view.py     KeyItem + KeyboardView (QGraphicsView, custom selection)
  proto.py             native HID protocol (pure packet builders + Keyboard class)
  keys.py              HID key codes and categories
  core.py              i18n, themes, layouts, profiles, settings
  state.py             color resolution, snapshots, undo/redo history
  worker.py            HardwareRunner (single-thread QThreadPool)
  gfx.py               drawing helpers, palettes and QSS stylesheets
  dialogs.py           manual/PDF, about, licenses, gradient, profile manager, udev
  widgets.py           Dot, logo, sidebar buttons, splash
lang/                  one XML per language and one HTML manual per language
assets/                app icon and SVG icons (Lucide)
packaging/             PyInstaller, Inno Setup, .desktop, install scripts
tests/                 pytest
```

### Protocol

`proto.py` separates packet construction (pure functions: `key_packets`, `whole_keyboard_packets`, `effect_packet`) from device access (`Keyboard`, built on `hidapi`). All output reports are 32 bytes, zero-padded. Whole-keyboard color updates use a prepare header, marker bytes in the first packet and a commit packet. `Keyboard` ranks the device's HID interfaces and lets you force a specific path.

### UI and data

- Editing works on an in-memory state; the hardware only changes on *Apply*, an effect, or live mode.
- Every change stores a snapshot (`History`); the window title shows `*` when there are unsaved changes.
- Sending runs in `HardwareRunner`; errors appear in a dialog, or in the status bar in live mode.
- Texts live in `lang/xx.xml` (`<s id="...">`, `{n}` placeholders), loaded by `I18N` and looked up with `tr()`.
- Settings and profiles are stored in `~/.config/drevo-light/` (or the platform equivalent); files from version 1.0 are migrated.

## Tests

```bash
pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

42 tests: protocol equivalence with `dtv2`, mouse selection, undo, profiles, imports, sending with a fake keyboard, translations and manual PDF. CI (`.github/workflows/ci.yml`) runs them on Linux and Windows.

## Packaging

- `packaging/build_linux.sh` / `build_windows.bat`: PyInstaller executables (`packaging/drevo-light.spec`).
- `packaging/drevo-light.iss`: Windows installer (Inno Setup).
- `clean.sh` / `clean.bat`: remove the virtual environment, caches and build output before committing.

Only the Linux PyInstaller build has been verified.

## License

GPL-3.0-or-later (see `LICENSE`). Lucide icons (ISC). `dtv2` (CC-BY-NC-SA) is used only as a reference in the tests and is not distributed. Details in `THIRD_PARTY_LICENSES.txt`.

Copyright (C) 2026 candion <candion@gmail.com>
