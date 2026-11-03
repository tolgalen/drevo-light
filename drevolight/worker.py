# Drevo Light - Copyright (C) 2026 candion <candion@gmail.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the
# terms of the GNU General Public License, version 3 or (at your option) any later
# version. It is distributed WITHOUT ANY WARRANTY. See the LICENSE file.
"""Runs keyboard commands on a background thread so the window never freezes."""
from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

from . import proto


class _Signals(QObject):
    finished = Signal(int, str)  # job id, error text ('' = success)


class _Job(QRunnable):
    def __init__(self, job_id, fn, path, signals):
        super().__init__()
        self.job_id, self.fn, self.path, self.signals = job_id, fn, path, signals

    def run(self):
        try:
            self.fn(proto.Keyboard(forced_path=self.path))
            error = ""
        except Exception as e:  # noqa: BLE001
            error = str(e) or e.__class__.__name__
        self.signals.finished.emit(self.job_id, error)


class HardwareRunner(QObject):
    """One job at a time (single worker thread), results delivered on the GUI thread."""
    done = Signal(object, str)  # (context, error)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = QThreadPool(self)
        self.pool.setMaxThreadCount(1)
        self._signals = _Signals(self)
        self._signals.finished.connect(self._finished)
        self._next, self._ctx = 0, {}

    @property
    def pending(self):
        return len(self._ctx)

    def submit(self, fn, path=None, context=None):
        self._next += 1
        self._ctx[self._next] = context
        self.pool.start(_Job(self._next, fn, path, self._signals))

    def wait(self):
        self.pool.waitForDone()

    def _finished(self, job_id, error):
        self.done.emit(self._ctx.pop(job_id, None), error)
