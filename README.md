# Drevo Light

Editor de iluminación para el teclado **Drevo Tyrfing V2** (USB `0416:a0f8`) escrito en Python con PySide6. Funciona en Linux y Windows sin el software oficial.

> Estado: el protocolo está verificado byte a byte contra la librería de referencia `dtv2` con un HID simulado, pero **aún no se ha probado con un teclado físico**.

## Características

- Teclado visual realista para seleccionar teclas (clic, arrastre de áreas, Ctrl alterna, Mayús reemplaza) y pintarlas.
- Distribuciones US ANSI y UK/ES/DE/FR/IT ISO, en versión completa y TKL.
- Pestañas de colores (por tecla, grupos y filas, degradados, colores recientes), efectos del teclado (estático, respiración, radar, flujo, …) y aplicación en vivo.
- Deshacer/rehacer (hasta 100 pasos) y copiar/pegar color.
- 20 perfiles (colores, efecto, modo y distribución), importación/exportación JSON validada.
- 6 idiomas (es, en, fr, it, de, pt) y 5 temas (sistema, claro, oscuro, azul oscuro, Drevo).
- Manual de usuario integrado, imprimible y exportable a PDF.
- Envío al teclado en segundo plano (la interfaz no se bloquea) y reaplicación del perfil al reconectar.

## Requisitos y ejecución

Python 3.10 o superior.

```bash
./run.sh          # Linux/macOS: crea .venv, instala dependencias y arranca
run.bat           # Windows
python -m drevolight   # si ya tienes las dependencias instaladas
```

En Linux se necesita una regla udev para acceder al dispositivo: menú *Archivo → Instalar reglas udev* (usa `pkexec`) o `packaging/install_linux.sh`. La regla usa `TAG+="uaccess"`, es decir, acceso solo para el usuario con sesión iniciada.

## Arquitectura

```
drevo_light.py         lanzador
drevolight/
  app.py               main(): QApplication, splash, ventana
  window.py            MainWindow: menús, páginas, perfiles, conexión
  keyboard_view.py     KeyItem + KeyboardView (QGraphicsView, selección propia)
  proto.py             protocolo HID nativo (constructores de paquetes puros + clase Keyboard)
  keys.py              códigos HID de teclas y categorías
  core.py              i18n, temas, distribuciones, perfiles, ajustes
  state.py             resolución de colores, instantáneas, historial deshacer/rehacer
  worker.py            HardwareRunner (QThreadPool de un hilo)
  gfx.py               utilidades de dibujo, paletas y hojas de estilo QSS
  dialogs.py           manual/PDF, acerca de, licencias, gradiente, gestor de perfiles, udev
  widgets.py           Dot, logo, botones laterales, splash
lang/                  un XML por idioma y un manual HTML por idioma
assets/                icono de la app y iconos SVG (Lucide)
packaging/             PyInstaller, Inno Setup, .desktop, scripts de instalación
tests/                 pytest
```

### Protocolo

`proto.py` separa la construcción de paquetes (funciones puras: `key_packets`, `whole_keyboard_packets`, `effect_packet`) del acceso al dispositivo (`Keyboard`, sobre `hidapi`). Todos los informes de salida son de 32 bytes, rellenados con ceros. Los colores completos usan una cabecera de preparación, marcadores en el primer paquete y un paquete de confirmación. `Keyboard` ordena las interfaces HID del dispositivo y permite forzar una ruta concreta.

### Interfaz y datos

- La edición trabaja sobre un estado en memoria; el hardware solo cambia con *Aplicar*, un efecto o el modo en vivo.
- Cada cambio guarda una instantánea (`History`); el título muestra `*` si hay cambios sin guardar.
- El envío se hace en `HardwareRunner`; los errores se muestran en un cuadro o en la barra de estado (modo en vivo).
- Los textos viven en `lang/xx.xml` (`<s id="…">`, marcadores `{n}`), cargados por `I18N` y consultados con `tr()`.
- Ajustes y perfiles: `~/.config/drevo-light/` (o el equivalente de cada sistema); se migran los ficheros de la versión 1.0.

## Pruebas

```bash
pip install -r requirements.txt -r requirements-dev.txt
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

42 pruebas: equivalencia del protocolo con `dtv2`, selección con ratón, deshacer, perfiles, importaciones, envío con teclado simulado, traducciones y PDF del manual. El CI (`.github/workflows/ci.yml`) las ejecuta en Linux y Windows.

## Empaquetado

- `packaging/build_linux.sh` / `build_windows.bat`: ejecutables con PyInstaller (`packaging/drevo-light.spec`).
- `packaging/drevo-light.iss`: instalador de Windows (Inno Setup).
- `clean.sh` / `clean.bat`: borran entorno virtual, cachés y compilaciones antes de subir a git.

Solo se ha verificado la compilación de PyInstaller en Linux.

## Licencias

GPL-3.0-or-later (ver `LICENSE`). Iconos Lucide (ISC). `dtv2` (CC-BY-NC-SA) se usa únicamente como referencia en las pruebas y no se distribuye. Detalles en `THIRD_PARTY_LICENSES.txt`.

© 2026 candion <candion@gmail.com>
