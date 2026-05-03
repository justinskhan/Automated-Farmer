"""UI scaling helper for high-DPI rendering.

In the browser, pygame renders to a canvas at physical pixel resolution
(devicePixelRatio-multiplied). All hardcoded UI dimensions must be multiplied
by the same factor so visual size stays correct while text renders at native
pixel sharpness. On desktop, the scale factor is 1.0.

A 2x multiplier is applied in the browser on top of devicePixelRatio so the
UI feels appropriately sized on large viewports — pygbag canvases tend to fill
the whole browser window, and the original logical layout was sized for a
1280x720 desktop window.
"""

import sys

_SCALE: float | None = None
_BROWSER_BOOST = 2.0  # multiplier applied on top of DPR in browser


def get_scale() -> float:
    global _SCALE
    if _SCALE is not None:
        return _SCALE
    if sys.platform in ("emscripten", "wasi"):
        try:
            import platform
            dpr = float(platform.window.devicePixelRatio) or 1.0
            _SCALE = dpr * _BROWSER_BOOST
            return _SCALE
        except Exception:
            _SCALE = _BROWSER_BOOST
            return _SCALE
    _SCALE = 1.0
    return 1.0


def s(v) -> int:
    """Scale and round an integer dimension by the UI scale factor."""
    return int(v * get_scale())
