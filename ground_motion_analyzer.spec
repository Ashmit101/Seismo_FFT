# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import (
    collect_data_files,
    collect_dynamic_libs,
    collect_submodules,
    copy_metadata,
)

datas = []
binaries = []
hiddenimports = []

# ObsPy discovers its readers through entry points and checks their dependencies.
datas += copy_metadata('obspy', recursive=True)
datas += collect_data_files('obspy')
# ObsPy's ctypes libraries (e.g. mseed.*.so) do not use the default lib*.so name.
binaries += collect_dynamic_libs(
    'obspy', search_patterns=['*.so', '*.pyd', '*.dll', '*.dylib']
)
hiddenimports += collect_submodules('obspy.io')
hiddenimports += collect_submodules('obspy.core')


a = Analysis(
    ['ground_motion_analyzer/__main__.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
    # ObsPy 1.4.x locates RELEASE-VERSION via inspect.currentframe(). Frozen
    # bytecode has a relative filename; loading this module from source gives
    # it the actual bundle path instead of the process's working directory.
    module_collection_mode={'obspy.core.util.version': 'py'},
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ground_motion_analyzer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
