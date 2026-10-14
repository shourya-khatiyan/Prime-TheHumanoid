# pyinstaller spec: one-file windows exe that serves the built frontend.
# build with ../build.ps1 (builds the frontend first).
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules

hidden = (
    collect_submodules("app")
    + collect_submodules("uvicorn")
    + collect_submodules("can.interfaces")
    + collect_submodules("fibre")
    + ["odrive", "libusb_package"]
)
datas = (
    [("metadata", "metadata"), ("profiles", "profiles"), ("../frontend/dist", "frontend_dist")]
    + collect_data_files("odrive")
    + collect_data_files("libusb_package")
)

a = Analysis(
    ["run.py"],
    pathex=["."],
    binaries=collect_dynamic_libs("libusb_package"),
    datas=datas,
    hiddenimports=hidden,
    excludes=["matplotlib", "IPython", "tkinter"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], name="vayn-odrv", console=True, upx=False)
