# build_exe_stop.py
# Creeaza executabil pentru opreste_catalog_online.py

import PyInstaller.__main__
import os

if __name__ == "__main__":
    args = [
        'opreste_catalog_gui.py',   # varianta cu interfata grafica
        '--onefile',
        '--windowed',               # fara consola
        '--name=Opreste-Catalog-Online',
        '--clean',
        '--noconfirm',
    ]
    PyInstaller.__main__.run(args)
    print("Executabil creat: {}".format(os.path.abspath('dist/Opreste-Catalog-Online.exe')))
