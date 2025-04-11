# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[('venv/Lib/site-packages/pyzbar/libiconv.dll', '.'), ('venv/Lib/site-packages/pyzbar/libzbar-64.dll', '.')],
    datas=[('core', 'core'), ('models', 'models'), ('ui', 'ui'), ('utils', 'utils')],
    hiddenimports=['winshell'],
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
    name='WinOTP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='ui/static/icons/app.ico'
)
