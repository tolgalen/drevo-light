# Drevo Light

Lighting editor for the **Drevo Tyrfing V2** keyboard (USB `0416:a0f8`), written in Python with PySide6. It lets you paint keys on a realistic on-screen keyboard, manage profiles, preview and start the keyboard's built-in effects, all without the official software. Runs on Linux and Windows.

> **Status.** The HID protocol was verified byte for byte against the reference library [`dtv2`](https://pypi.org/project/dtv2/) using a simulated HID device, and the whole-keyboard color, per-key/group colors and the static, breathing, radar, stream and memory effects were confirmed on a physical Drevo Tyrfing V2 (Linux, GNOME/Wayland, 2026-11-06), as were column selection, the tray icon and the PC-driven animations (including the Start/Stop button). Only lighting is supported (no key remapping or macros). Only the Linux PyInstaller build has been verified.

## Table of contents

1. [Features](#features)
2. [Installation and running](#installation-and-running)
3. [Linux permissions (udev)](#linux-permissions-udev)
4. [Using the application](#using-the-application)
5. [Profiles and configuration files](#profiles-and-configuration-files)
6. [Architecture](#architecture)
7. [HID protocol](#hid-protocol)
8. [Internationalization](#internationalization)
9. [Themes](#themes)
10. [Testing and CI](#testing-and-ci)
11. [Packaging](#packaging)
12. [Security notes](#security-notes)
13. [Troubleshooting](#troubleshooting)
14. [Limitations and roadmap](#limitations-and-roadmap)
15. [Contributing](#contributing)
16. [License](#license)

## Features

**Editing**
- Realistic visual keyboard (QGraphicsView) with per-key legends, LED glow and selection highlight.
- Layouts: US (ANSI) and UK, ES, DE, FR, IT (ISO), each in full-size and TKL versions.
- Selection: click toggles a key; a plain drag *adds* an area (several areas can be accumulated); `Ctrl` + drag toggles; `Shift` + drag replaces; click on the background clears. Buttons for all / none / invert, key groups (letters, digits, F-keys, modifiers, editing, arrows), whole rows and whole columns.
- Painting: color picker, presets, recent colors (persisted), custom colors (persisted), two-color or rainbow gradients (horizontal/vertical), copy/paste color.
- The editor starts from an unlit keyboard (black base); a base color and per-group colors are available in the *Colors* tab, and a table lets you type key names (with validation and autocompletion) and *Add selection*.
- Undo / redo (up to 100 steps, includes *Clear editor*).
- *Live apply* sends changes to the keyboard as you edit (debounced).

**Hardware**
- Whole-keyboard color, per-key colors, group colors, *Turn lights off* and *Reset keyboard*.
- Built-in effects stored in the keyboard firmware: static, breathing, radar, stream, memory; with two colors, brightness, speed, direction and rainbow where applicable.
- Hotplug detection: the connection panel refreshes when the keyboard is plugged in or out, and the active profile can be re-applied automatically.
- Commands run on a background thread; the UI never blocks.

- PC-driven animations (rainbow wave, scanner, color wave): the PC streams per-key frames at 15 fps over one open HID session (~19 ms per frame); any other command to the keyboard stops them. Use the colors, brightness and speed of the Effects tab.

**Effect preview**
- The *Effects* tab always shows the keyboard layout with an animated approximation of the selected effect, following the controls live. It pauses (and its clock freezes) when you leave the tab. In *Memory* mode, click keys to "press" them.

**Application**
- System tray icon (when the desktop provides one; GNOME needs the AppIndicator extension): show/hide the window, switch profile (applies it to the keyboard), lights off, quit; optional *close to the system tray*.
- 20 profile slots (colors, effect, last mode, layout), manager with thumbnails, import/export to JSON, optional apply-on-load / apply-on-start.
- 6 languages (es, en, fr, it, de, pt) and 5 themes (system, light, dark, dark blue, Drevo); selectable from the menu bar.
- Built-in user manual in each language, printable and exportable to PDF (`F1`).
- Unsaved-changes tracking (`*` in the window title), remembered window geometry, optional splash screen.

## Installation and running

Requirements: Python 3.10 or newer (CI runs 3.12; developed on 3.14), `hidapi` and `PySide6` (pinned in `requirements.txt`).

```bash
git clone https://github.com/tolgalen/drevo-light.git
cd drevo-light

./run.sh               # Linux/macOS: creates .venv, installs dependencies, starts the app
run.bat                # Windows: same
python -m drevolight   # if the dependencies are already installed
```

`run.sh` prefers Python 3.13/3.12/3.11/3.10 when available. On Debian/Ubuntu it needs `python3-venv`. If no prebuilt `hidapi` wheel exists for your Python (typically a very new release), pip compiles it and needs development packages; the script prints the exact command for your distribution:

| Distribution | Packages |
|---|---|
| Fedora / RHEL | `sudo dnf install libusb1-devel systemd-devel gcc python3-devel` |
| Debian / Ubuntu | `sudo apt install libusb-1.0-0-dev libudev-dev gcc python3-dev python3-venv` |
| Arch | `sudo pacman -S libusb base-devel` |

If `hidapi` is missing the GUI still starts and explains what to install.

## Linux permissions (udev)

Without a udev rule only root can open the keyboard's HID interfaces. Choose one:

1. Menu *File → Install udev rules (Linux)…* (asks for administrator rights through `pkexec`).
2. `packaging/install_linux.sh` (installs the application menu entry, the icon and the rule; use `--no-udev` to skip the rule).
3. Manually:
   ```bash
   sudo install -m 644 70-drevo-tyrfing.rules /etc/udev/rules.d/
   sudo udevadm control --reload && sudo udevadm trigger
   ```
   Then unplug and plug the keyboard again.

The rule grants access with `TAG+="uaccess"`, i.e. only to the logged-in local user (not world-writable).

## Using the application

### Window layout
- **Top:** connection status (colored dot, message, last command), interface selector (*Automatic* or a specific HID interface), *Re-detect*, *USB diagnostics* and *Check now*.
- **Sidebar:** *Keyboard*, *Colors*, *Effects*.
- **Menu bar:** File, Edit, Profiles, Theme, Language, Help; the right corner shows the layout size and key count.
- **Status bar:** last message and the official website link.

### Keyboard tab
Layout and size combos, the selection toolbar (*All, None, Invert, Letters, Numbers, F-keys, Modifiers, Editing, Arrows, rows 1-6*), the color of the selection (*Paint selection*, presets, *Remove color*), recent colors, *Copy/Paste color*, *Gradient…*, and the action row: *Apply to keyboard*, *Turn lights off*, *Reset keyboard*, *Clear editor* (affects only the editor, never the hardware) and *Live apply*.

### Colors tab
Base color, group colors (letters, digits, function, modifiers, editing, arrows) and a table of per-key colors. Color priority is: **individual key > enabled group > base color**.

### Effects tab
Effect, color 1/2, brightness, speed, rainbow, direction (stream) and *Apply effect*, plus the live preview below. The effect runs inside the keyboard once applied.

### Keyboard shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+Z` | Undo |
| `Ctrl+Y` / `Ctrl+Shift+Z` | Redo |
| `Ctrl+C` / `Ctrl+V` | Copy / paste color |
| `Ctrl+A` | Select all keys |
| `F1` | User manual |
| `Ctrl+Q` | Quit |
| Drag / `Ctrl`+drag / `Shift`+drag | Add area / toggle / replace selection |

## Profiles and configuration files

Settings and profiles live in the per-user config folder:

| Platform | Folder |
|---|---|
| Linux | `$XDG_CONFIG_HOME/drevo-light/` (default `~/.config/drevo-light/`) |
| Windows | `%APPDATA%\drevo-light\` |
| macOS | `~/Library/Application Support/drevo-light/` |

Files: `settings.json` (language, theme, layout, size, active profile, live / apply-on-load / apply-on-start flags, splash, recent and custom colors, window geometry) and `profiles.json` (`{"slots": [...]}` with 20 entries, each `null` or `{"name": str, "data": {...}}`). Files from version 1.0 (`~/.drevo_light*.json`) are migrated automatically.

A profile (also the exported `.json`) has this shape:

```json
{
  "base": "#000000",
  "categories": {"letters": {"on": true, "color": "#ff0000"}, "digits": {"on": false, "color": "#ffffff"}},
  "keys": {"esc": "#00ff00", "a": "#0000ff"},
  "layout": {"id": "es", "size": "tkl"},
  "effect": {"effect": 1, "bright": 100, "speed": 60, "dir": 0, "rainbow": false,
             "colors": ["#ff0000", "#0000ff"]},
  "mode": "colors"
}
```

Imported files are validated and sanitized (unknown keys/colors/ranges are discarded) before use.

## Architecture

```
drevo_light.py         launcher (python drevo_light.py)
drevolight/
  app.py               main(): QApplication, splash, main window
  window.py            MainWindow: construction, menus, settings/theme, undo/redo (composes the mixins below)
  page_keyboard.py     KeyboardPageMixin: keyboard tab, selection and painting
  page_colors.py       ColorsPageMixin: colors tab (base, groups, per-key table)
  page_effects.py      EffectsPageMixin: effects tab
  hardware.py          HardwareMixin: connection state/polling and commands sent to the keyboard
  profiles.py          ProfilesMixin: 20 profile slots, import/export
  anim.py              PC-driven animations: pure frame function + streaming thread
  tray.py              TrayMixin: system tray icon (profiles, lights off, close to tray)
  common.py            shared constants and small helpers
  keyboard_view.py     KeyItem + KeyboardView (QGraphicsView, custom area selection)
  preview.py           effect simulation (pure) + PreviewPanel (embedded animation)
  proto.py             native HID protocol: pure packet builders + Keyboard class
  keys.py              HID usage codes, key order, categories, numpad keys
  core.py              i18n, themes, layouts, profiles/settings I/O, constants
  state.py             color resolution, snapshots, gradients, undo/redo History
  worker.py            HardwareRunner (single-thread QThreadPool, `done` signal)
  gfx.py               drawing helpers, system palette, QSS stylesheet, SVG icons
  dialogs.py           manual/PDF, about, licenses, gradient, profile manager, udev installer
  widgets.py           status Dot, logo, sidebar buttons, splash
lang/                  one XML per language + manual_xx.html per language
assets/                app icon (png/ico), Lucide SVG icons
packaging/             PyInstaller spec, build scripts, Inno Setup, .desktop, installer
tests/                 pytest suite
```

Design notes:
- **Pure core.** `proto.py` packet builders, `state.py` and the effect simulation in `preview.py` contain no Qt/hardware access, so they are unit-testable.
- **Editor state vs. hardware.** The editor keeps colors in memory (`base`, `cat_enabled/cat_color`, `keys`). The hardware changes only on *Apply*, an effect, or live mode. Every change stores a snapshot in `History`.
- **Threading.** Hardware jobs are submitted to `HardwareRunner`; results come back through a Qt signal. Errors are shown in a dialog, or only in the status bar in live mode. The window waits for pending jobs on close, and polling pauses while a command is in flight.
- **UI rebuild.** Changing theme, language or layout rebuilds the interface (`build_ui`), preserving the selection.
- **Preview.** `effect_colors(name, t, params, positions, extent, presses)` returns the color of every key at time `t`; `PreviewPanel` drives it with a 33 ms timer that runs only while visible.

## HID protocol

Every command is a **32-byte HID output report**, zero-padded, written with `hidapi`. Only the first 7 bytes identify the command.

| Command | Header (hex) |
|---|---|
| Per-key colors | `06 BE 19 00 01 01 0E` |
| Prepare (before whole-keyboard paint) | `06 BE 15 00 01 01 0F` |
| Commit (after whole-keyboard paint) | `06 BE 15 00 02 01 01` |
| Effect: static / breath / stream / memory / radar | `06 BE 15 00 01 01` + `01` / `02` / `03` / `0D` / `10` |

- **Key colors:** up to 5 keys per packet; for key *i*, byte `7+i` is the HID usage code and bytes `12+4i … 14+4i` are R, G, B.
- **Whole keyboard:** prepare packet (`[8]=0x06`, `[12]=0xFF`), key packets for all 106 keys in `KEY_ORDER` (first packet carries marker bytes `[15]=0x53`, `[31]=0x65`), commit packet (`[7]=0x05`, `[8]=0x09`, `[12]=[16]=0xFF`).
- **Effects:** one packet. Speed `[7]` = `round(speed/100*9)` (not for memory), brightness `[8]` = `round(brightness/100*6)`, direction `[9]` (`e=0, w=1, s=2, n=3`), rainbow `[15]`, color 1 `[12:15]`, color 2 `[16:19]`.
- **Interface choice:** `Keyboard` ranks the device's HID interfaces (interface 1 with usage 0 first, then other interface 1, then vendor-defined pages) and tries them in order; *Automatic* or a forced path can be chosen in the UI.
- **Differences with `dtv2`:** `dtv2` sometimes sends shorter packets for partial groups; this project always sends 32 bytes. The *modifiers* group is the same set used by the on-screen preview.

If you can capture traffic from the official software, additions (remapping, macros, other effects) are welcome as pure builders plus tests.

## Internationalization

- Each language is `lang/<code>.xml`:
  ```xml
  <language code="en" name="English">
    <s id="app.title">Drevo Light - Tyrfing V2</s>
    <s id="kb.count">{n} keys selected</s>
  </language>
  ```
  Placeholders use `{name}`; `\n` is a literal line break. Use `tr("id", n=3)` in code.
- The user manual is `lang/manual_<code>.html` (HTML subset rendered by `QTextBrowser`/`QTextDocument`).
- **Add a language:** copy `lang/en.xml` and `lang/manual_en.html`, change `code`/`name`, translate. It appears in the *Language* menu automatically. The test suite checks that every language has exactly the same ids and placeholders, and that every `tr("...")` used in the code exists.
- The default language comes from the system locale; the default layout follows the language when a matching layout exists.
- Translations other than Spanish and English have not been reviewed by native speakers.

## Themes

`core.THEMES` defines palettes for `light`, `dark`, `navy` (dark blue) and `drevo`; `system` uses Fusion with the operating system palette captured at startup and the same stylesheet (`gfx.system_palette` derives the extra colors). All themes are applied through one QSS generator (`gfx.stylesheet`) plus the custom painting of keys, which reads the palette (`rim`, `face`, `legend_*`, `canvas`, `panel`, …). To add a theme, add a palette to `THEMES` and its id to `THEME_IDS`, and add the `theme.<id>` string to every language file.

## Testing and CI

```bash
pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

44 tests; the window tests use a fixture with fixed settings (language `es`, layout `es`, TKL) and a fake keyboard so they do not depend on the machine locale or hardware.

| File | Covers |
|---|---|
| `tests/test_proto.py` | Byte-for-byte equivalence with `dtv2` (using a fake HID), key codes and order, groups, effects, invalid input, no-keyboard error |
| `tests/test_window.py` | Mouse selection, undo/redo, gradient, recent colors, key validation, worker-based apply, live mode, error reporting, 20 profile slots, import sanitizing, manual PDFs, translation consistency, udev command, settings, effect preview and its lifecycle |
| `tests/test_smoke.py` | The window builds with every theme and language |

CI also runs `ruff check .` (see `ruff.toml`).

`dtv2` is a development-only dependency (CC-BY-NC-SA) and is not used at runtime. GitHub Actions (`.github/workflows/ci.yml`) runs the suite on Ubuntu and Windows for every push and pull request, and builds PyInstaller artifacts for tags matching `v*`.

## Packaging

| Item | How |
|---|---|
| Linux executable folder | `packaging/build_linux.sh` → `dist/drevo-light/drevo-light` |
| Windows executable | `packaging\build_windows.bat` → `dist\drevo-light\drevo-light.exe` |
| Windows installer | `packaging/drevo-light.iss` (Inno Setup; run automatically by the batch file if `iscc` is on PATH) |
| Linux menu entry | `packaging/drevo-light.desktop` + `packaging/install_linux.sh` |
| PyInstaller spec | `packaging/drevo-light.spec` (bundles `lang/`, `assets/`, license files, the udev rule; excludes unused Qt modules) |
| Clean for git | `./clean.sh` (or `clean.bat`) removes the virtual environment, caches and build output; `./clean.sh -n` is a dry run |

Windows/macOS builds and the Inno Setup installer have not been run by the author.

## Security notes

- No network access, `eval`/`exec`, `pickle` or `shell=True`.
- Imported profiles are validated; language and manual files come from the installation.
- The udev installer embeds the rule text in the code and writes it through `pkexec`, instead of copying a file from the (user-writable) install folder; the rule uses `uaccess`, not `MODE="0666"`.
- The keyboard receives only fixed-length packets built from validated values.

## Troubleshooting

| Symptom | Likely cause / action |
|---|---|
| "Keyboard NOT detected" | Check the cable and VID/PID `0416:a0f8`; press *USB diagnostics* for the list of HID devices seen. |
| Detected but "no access" (yellow) | Linux: install the udev rule and replug. Windows: close the official Drevo software in case it is holding the device (not verified). |
| "hidapi not available" | `pip install hidapi` in the app environment (`./run.sh` does it for you). |
| Some commands fail, others work | Pick another HID interface in the interface combo and *Check now*; send the *USB diagnostics* output when reporting. |
| Settings look odd | Delete the files in the config folder (see above). |
| `Could not load the Qt platform plugin "xcb"` on Linux | Install `libxcb-cursor0` (Debian/Ubuntu) or the equivalent for your distribution. |

## Limitations and roadmap

- Hardware-tested only on one keyboard and on Linux; Windows is untested. Brightness/speed/direction values and the profile apply flow have not been checked on the device.
- No key remapping, macros or firmware profile storage (needs protocol captures from the official software).
- The effect preview is an approximation of the firmware effects.
- Translations other than es/en need native review; the logo is an approximation of the official one.
- Ideas: more PC-driven animations (e.g. music or CPU reactive), automatic profile per active application (not possible in a generic way on Wayland), reduce UI rebuilds when changing theme/language, `mypy` in CI, clean up unused imports (F401 is currently ignored by `ruff`).

## Contributing

Issues and pull requests are welcome. Please keep code and comments in English, add tests for behavior changes (`pytest` must pass), keep all `lang/*.xml` files in sync, and avoid new dependencies without discussion. Protocol additions must come with packet builders in `proto.py` and tests; do not send untested commands to a real keyboard.

## License

GPL-3.0-or-later (see `LICENSE`). Third-party notices in `THIRD_PARTY_LICENSES.txt` (Lucide icons: ISC; PySide6/Qt: LGPL; `hidapi`; `dtv2`: CC-BY-NC-SA, used only as a test reference and not distributed). The HID protocol is based on the documentation by David Cobac in `dtv2`; the code in `proto.py` was written independently.

Copyright (C) 2026 candion <candion@gmail.com>
