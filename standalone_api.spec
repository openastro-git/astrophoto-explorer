# -*- mode: python ; coding: utf-8 -*-
# Astrophoto Explorer - PyInstaller Configuration

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
        'tifffile'
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

splash = Splash(
    'splash_screen.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=None,
    text_size=12,
    always_on_top=True
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    [],
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
    icon='icon.ico'
)

coll = COLLECT(
    exe,
    splash.binaries,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='astrophoto-explorer'
)
