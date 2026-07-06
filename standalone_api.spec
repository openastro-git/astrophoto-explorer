# -*- mode: python ; coding: utf-8 -*-
# Astrophoto Explorer - PyInstaller Configuration
import sys

block_cipher = None

a = Analysis(
    ['standalone_api.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('backend', 'backend'),
        ('ui', 'ui'),
        ('pyongc_data', 'pyongc')
    ],
    hiddenimports=[
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.logging',
        'fastapi',
        'websockets',
        'astropy.io.fits',
        'astropy.wcs',
        'numpy',
        'numpy.testing',
        'numpy.linalg._umath_linalg',
        'scipy',
        'scipy.ndimage',
        'scipy.special._ufuncs_cxx',
        'scipy._lib.array_api_compat',
        'PIL._tkinter_finder',
        'asyncio',
        'unittest',
        'unittest.mock',
        'webview',
        'tifffile',
        'clr',
        'clr_loader'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'test',
        'doctest'
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Splash screen is not supported on macOS
show_splash = sys.platform != 'darwin'

if show_splash:
    splash = Splash(
        'splash_screen.png',
        binaries=a.binaries,
        datas=a.datas,
        text_pos=None,
        text_size=12,
        always_on_top=True
    )
    exe_args = [pyz, a.scripts, splash, []]
else:
    splash = None
    exe_args = [pyz, a.scripts, []]

exe = EXE(
    *exe_args,
    exclude_binaries=True,
    name='astrophoto-explorer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None if sys.platform == 'darwin' else 'icon.ico'
)

if show_splash:
    coll_args = [exe, splash.binaries, a.binaries, a.zipfiles, a.datas]
else:
    coll_args = [exe, a.binaries, a.zipfiles, a.datas]

coll = COLLECT(
    *coll_args,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='astrophoto-explorer'
)
