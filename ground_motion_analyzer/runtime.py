"""Standalone app setup."""

import logging
import os
import sys
from pathlib import Path
from tempfile import TemporaryFile


def configure_matplotlib_cache():
    """Use a reusable Matplotlib cache in frozen builds."""
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
        with TemporaryFile(dir=cache_dir):
            pass
    except (OSError, RuntimeError) as error:
        logging.getLogger(__name__).warning(
            "Cannot use persistent Matplotlib cache; keeping temporary cache: %s",
            error,
        )
        return None

    os.environ["MPLCONFIGDIR"] = str(cache_dir)
    return cache_dir
