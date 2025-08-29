import os, shutil
import config

def init_exec_paths():
    base_path = os.path.join(config.APPDATA, "OTClientV8", "Aurera")
    fallback = os.path.join(config.APPDATA, "AureraOT", "aurera_dx.exe")
    exe = os.path.join(base_path, "aurera_dx.exe")

    if not os.path.exists(exe):
        if os.path.exists(fallback):
            os.makedirs(base_path, exist_ok=True)
            shutil.copy2(fallback, exe)
        else:
            raise FileNotFoundError("Executável não encontrado")

    dst = os.path.join(base_path, "aurera_dx2.exe")
    if os.path.exists(dst):
        os.remove(dst)
    shutil.copy2(exe, dst)

    config.EXECUTAVEL = exe
    config.EXECUTAVEL2 = dst
