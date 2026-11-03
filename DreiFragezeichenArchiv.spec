# -*- mode: python ; coding: utf-8 -*-
#
# Bauanleitung für PyInstaller – Die Drei ??? – Archivverwaltung
#
# Aufruf (im Ordner C:\DreiFragezeichenArchiv_Programm):
#   .venv\Scripts\python.exe -m PyInstaller DreiFragezeichenArchiv.spec --noconfirm
#
# Ergebnis:
#   dist\DreiFragezeichenArchiv\DreiFragezeichenArchiv.exe
#   (der ganze Ordner dist\DreiFragezeichenArchiv gehört zum Programm)

import os

from PyInstaller.utils.hooks import collect_submodules

PROJECT_DIR = SPECPATH
APP_DIR = os.path.join(PROJECT_DIR, "app")

# Programmdateien, die mit ausgeliefert werden
datas = [
    (os.path.join(APP_DIR, "templates"), os.path.join("app", "templates")),
    (os.path.join(APP_DIR, "static"), os.path.join("app", "static")),
]

# Module, die erst zur Laufzeit geladen werden und von
# PyInstaller sonst nicht erkannt würden
hiddenimports = (
    collect_submodules("uvicorn")
    + [
        "backend",
        "clr",
        "webview.platforms.winforms",
        "webview.platforms.edgechromium",
    ]
)

a = Analysis(
    [os.path.join(PROJECT_DIR, "launcher", "start.py")],
    pathex=[APP_DIR],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="DreiFragezeichenArchiv",
    icon=os.path.join(APP_DIR, "static", "images", "blacky_archiv.ico"),
    console=False,          # kein Konsolenfenster
    debug=False,
    strip=False,
    upx=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="DreiFragezeichenArchiv",
)
