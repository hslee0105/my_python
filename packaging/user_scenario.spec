# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec: UserScenario.exe(GUI) + UserScenarioCLI.exe(콘솔) 를 한 폴더에 빌드
#
#   pyinstaller packaging/user_scenario.spec --noconfirm --clean
#   → dist/UserScenario/
#
# - 두 exe 가 같은 런타임(DLL, Playwright 드라이버 등)을 공유하도록 COLLECT 하나로 묶음
# - Playwright 는 Python 패키지 안의 드라이버(node.exe + JS)만 포함하고 브라우저는 포함하지 않음
#   → 배포본은 PC 에 설치된 Edge/Chrome(channel=msedge/chrome)을 사용
import os

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))

datas = collect_data_files("playwright")  # playwright/driver (node.exe, package/*)
hiddenimports = collect_submodules("user_scenario")
if os.name == "nt":
    hiddenimports += collect_submodules("pywinauto") + ["comtypes", "comtypes.client"]
excludes = ["PyQt5", "PyQt6", "PySide2", "PySide6", "IPython", "pytest"]


def analysis(script):
    return Analysis(
        [os.path.join(SPECPATH, script)],
        pathex=[ROOT],
        datas=datas,
        hiddenimports=hiddenimports,
        excludes=excludes,
        noarchive=False,
    )


a_gui = analysis("gui_app.py")
a_cli = analysis("cli_app.py")

exe_gui = EXE(
    PYZ(a_gui.pure), a_gui.scripts, [],
    exclude_binaries=True, name="UserScenario", console=False, upx=False,
)
exe_cli = EXE(
    PYZ(a_cli.pure), a_cli.scripts, [],
    exclude_binaries=True, name="UserScenarioCLI", console=True, upx=False,
)

coll = COLLECT(
    exe_gui, a_gui.binaries, a_gui.datas,
    exe_cli, a_cli.binaries, a_cli.datas,
    name="UserScenario", upx=False,
)
