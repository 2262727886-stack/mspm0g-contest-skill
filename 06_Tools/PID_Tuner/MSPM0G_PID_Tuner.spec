# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['PID_DEMO\\gui.py'],
    pathex=[],
    binaries=[],
    datas=[('config.example.json', '.')],
    hiddenimports=['serial', 'serial.tools.list_ports', 'openai', 'queue', 'tkinter', 'tkinter.ttk'],
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
    name='MSPM0G_PID_Tuner',
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
)
