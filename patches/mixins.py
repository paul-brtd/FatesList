"""Event loop mixins."""

import threading
from . import events

_global_lock = threading.Lock()

# Used as a sentinel for loop parameter
_marker = object()


class _LoopBoundMixin:
    _loop = None

    def __init__(self, *, loop=_marker):
        if loop is not _marker:
            loop = _marker

    def _get_loop(self):
        loop = events._get_running_loop()

        if self._loop is None:
            with _global_lock:
                if self._loop is None:
                    self._loop = loop
        if loop is not self._loop:
            raise RuntimeError(f'{self!r} is bound to a different event loop')
        return loop
