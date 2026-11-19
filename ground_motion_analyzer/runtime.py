"""Runtime setup for the standalone executable, without scientific imports."""

import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryFile


def configure_matplotlib_cache():
    """Replace PyInstaller's per-launch MPLCONFIGDIR with a persistent cache.

    Source runs keep Matplotlib's normal configuration and MPLCONFIGDIR behavior.
    The frozen build supports SEISMO_FFT_MPLCONFIGDIR as an explicit override,
    since PyInstaller overwrites MPLCONFIGDIR before application code executes.
    Call before importing matplotlib (including indirectly through ObsPy).
    """
    if not getattr(sys, "frozen", False):
        return None

    try:
        override = os.environ.get("SEISMO_FFT_MPLCONFIGDIR")
        if override:
            cache_dir = Path(override).expanduser().resolve()
        else:
            home = Path.home()
            if sys.platform == "win32":
                base = Path(
                    os.environ.get("LOCALAPPDATA") or home / "AppData" / "Local"
                )
            elif sys.platform == "darwin":
                base = home / "Library" / "Caches"
            else:
                base = Path(os.environ.get("XDG_CACHE_HOME") or home / ".cache")
            cache_dir = base / "Seismo_FFT" / "matplotlib"

        cache_dir.mkdir(parents=True, exist_ok=True)
        # Check actual write access rather than trusting permission bits. Keep
        # PyInstaller's temporary fallback if the user's cache is not writable.
        with TemporaryFile(dir=cache_dir):
            pass
    except (OSError, RuntimeError) as error:
        logging.getLogger(__name__).warning(
            "Cannot use persistent Matplotlib cache; keeping temporary cache: %s",
            error,
        )
        return None

    # Matplotlib 3.10 serializes bundled font paths relative to mpl-data, so the
    # cached index remains valid when a one-file build extracts to a new _MEI dir.
    os.environ["MPLCONFIGDIR"] = str(cache_dir)
    return cache_dir
