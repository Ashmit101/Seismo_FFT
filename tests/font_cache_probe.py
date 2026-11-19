"""Small frozen-build probe: run twice with the same SEISMO_FFT_MPLCONFIGDIR.

The second run must reuse the font index despite a different _MEIPASS directory.
This probe also renders text with a bundled font, catching stale extraction paths.
"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ground_motion_analyzer.runtime import configure_matplotlib_cache


def main():
    cache = configure_matplotlib_cache()
    if cache is None:
        raise RuntimeError(
            "Run this probe as a frozen executable with a writable cache."
        )
    before = {
        path.name: path.stat().st_mtime_ns for path in cache.glob("fontlist-*.json")
    }
    started = time.perf_counter()

    import matplotlib
    from matplotlib import font_manager
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    font = font_manager.findfont("DejaVu Sans", fallback_to_default=False)
    assert Path(font).is_file(), font
    figure = Figure()
    figure.text(0.5, 0.5, "Seismo FFT", fontfamily="DejaVu Sans")
    FigureCanvasAgg(figure).draw()
    after = {
        path.name: path.stat().st_mtime_ns for path in cache.glob("fontlist-*.json")
    }
    assert after, "Matplotlib did not write a font cache"
    assert Path(matplotlib.get_cachedir()) == cache
    print(
        json.dumps(
            {
                "cache_dir": str(cache),
                "extraction_dir": sys._MEIPASS,
                "cache_reused": bool(before) and before == after,
                "font_import_and_render_seconds": time.perf_counter() - started,
            }
        )
    )


if __name__ == "__main__":
    main()
