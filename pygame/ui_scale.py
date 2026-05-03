"""UI scaling helper for high-DPI rendering.

In the browser, pygame renders to a canvas at physical pixel resolution
(devicePixelRatio-multiplied). All hardcoded UI dimensions must be multiplied
by the same factor so visual size stays correct while text renders at native
pixel sharpness. On desktop, the scale factor is 1.0.
"""

import sys

_SCALE: float | None = None


def get_scale() -> float:
    global _SCALE
    if _SCALE is not None:
        return _SCALE
    if sys.platform in ("emscripten", "wasi"):
        try:
            import platform
            _SCALE = float(platform.window.devicePixelRatio) or 1.0
            return _SCALE
        except Exception:
            _SCALE = 1.0
            return 1.0
    _SCALE = 1.0
    return 1.0


def s(v) -> int:
    """Scale and round an integer dimension by the UI scale factor."""
    return int(v * get_scale())
