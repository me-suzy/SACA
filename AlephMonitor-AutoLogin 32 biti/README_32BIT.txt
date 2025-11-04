══════════════════════════════════════════════════════════════════
ALEPH MONITOR – VARIANTA 32-BIT
══════════════════════════════════════════════════════════════════

Ce conține:
- monitor-server-autologin.py – aplicația principală (GUI) 32-bit
- build_exe_autologin.py – build EXE (în funcție de Python folosit)
- opreste_catalog_gui.py – utilitar GUI „Oprește Catalog Online”
- build_exe_stop.py – build EXE pentru utilitarul de oprit
- start_aleph_monitor.bat – script pentru Task Scheduler (pornire)
- INSTRUCTIUNI_TASK_SCHEDULER.txt – ghid configurare Task Scheduler

IMPORTANT: Pentru executabil 32-bit trebuie Python 32-bit!
1) Instalează Python 3.12 32-bit (x86) din python.org
   – la instalare bifează „Add Python to PATH”
2) Deschide Command Prompt (nu PowerShell) în acest folder
3) Instalează dependențe (se instalează în Python-ul 32-bit):
   pip install --upgrade pip
   pip install paramiko requests psutil pyinstaller pillow
4) Creează EXE-ul principal (32-bit):
   python build_exe_autologin.py
   – rezultatul: dist\AlephMonitor-AutoLogin.exe (32-bit)
5) Creează EXE-ul „Oprește Catalog Online” (32-bit):
   python build_exe_stop.py
   – rezultatul: dist\Opreste-Catalog-Online.exe (32-bit)

Rulare automată (fără ferestre peste focus):
- Folosește start_aleph_monitor.bat în Task Scheduler (vezi ghidul)

Notă:
- Build-ul depinde DOAR de arhitectura Python care rulează PyInstaller.
  Dacă rulezi build-ul din Python 32-bit → EXE 32-bit.
  Dacă rulezi din Python 64-bit → EXE 64-bit.
