# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = ['uvicorn.logging', 'uvicorn.protocols.http', 'uvicorn.protocols.http.auto', 'uvicorn.protocols.http.h11_impl', 'uvicorn.protocols.websockets', 'uvicorn.protocols.websockets.auto', 'uvicorn.protocols.websockets.wsproto_impl', 'uvicorn.lifespan', 'uvicorn.lifespan.on', 'uvicorn.lifespan.off', 'httpx', 'httpcore', 'anyio', 'sniffio', 'h11', 'pydantic', 'pydantic_settings', 'dotenv']
hiddenimports += collect_submodules('uvicorn')
hiddenimports += collect_submodules('pydantic')
hiddenimports += collect_submodules('pydantic_settings')


a = Analysis(
    ['run_server.py'],
    pathex=[],
    binaries=[],
    datas=[('app', 'app')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ataai-backend',
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
