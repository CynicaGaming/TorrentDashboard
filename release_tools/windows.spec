# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

ROOT = Path(SPECPATH).resolve().parent


def analysis(entry):
    return Analysis(
        [str(ROOT / entry)],
        pathex=[str(ROOT)],
        binaries=[],
        datas=[],
        hiddenimports=[],
        hookspath=[],
        hooksconfig={},
        runtime_hooks=[],
        excludes=[],
        noarchive=False,
        optimize=0,
    )


def executable(a, name):
    pyz = PYZ(a.pure)
    return EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )


dashboard = analysis("dashboard.py")
recovery = analysis("recovery_tool.py")
updater = analysis("updater.py")

Dashboard = executable(dashboard, "Dashboard")
Recovery = executable(recovery, "Recovery")
Updater = executable(updater, "Updater")

bundle = COLLECT(
    Dashboard,
    Recovery,
    Updater,
    dashboard.binaries,
    dashboard.datas,
    recovery.binaries,
    recovery.datas,
    updater.binaries,
    updater.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="TorrentDashboard",
)
