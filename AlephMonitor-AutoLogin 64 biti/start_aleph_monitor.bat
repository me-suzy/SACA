@echo off
REM ============================================================
REM Script pentru Task Scheduler - Aleph Monitor Auto Login
REM ============================================================
REM
REM Acest script lansează AlephMonitor-AutoLogin.exe în background
REM fără a fura focusul sau a deschide ferestre peste aplicațiile active.
REM
REM Folosire în Task Scheduler:
REM   1. Creează task nou → "Trigger" la "At logon" sau "Daily"
REM   2. Action: Start a program → Browse către acest .bat
REM   3. Settings: ✓ Run whether user is logged on or not
REM   4. Settings: ✓ Hidden (pentru a nu arăta fereastră)
REM   5. Conditions: Opțional - dezactivează "Start only if computer is on AC power"
REM
REM ============================================================

REM Setează calea către folderul scriptului
cd /d "%~dp0"

REM Calea către executabil
set EXE_PATH=%~dp0dist\AlephMonitor-AutoLogin.exe

REM Verifică dacă executabilul există
if not exist "%EXE_PATH%" (
    echo [ERROR] Nu gasesc executabilul la: %EXE_PATH%
    echo Verifica ca executabilul a fost creat corect.
    pause
    exit /b 1
)

REM Verifică dacă procesul rulează deja
tasklist /FI "IMAGENAME eq AlephMonitor-AutoLogin.exe" 2>NUL | find /I /N "AlephMonitor-AutoLogin.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [INFO] AlephMonitor-AutoLogin.exe ruleaza deja. Nu se mai lanseaza o instanta.
    exit /b 0
)

REM Lansează executabilul minimizat (fără fereastră de consolă)
REM START /MIN = minimizează fereastra
REM START /B = rulează în background (fără fereastră nouă)
echo [INFO] Lansare AlephMonitor-AutoLogin.exe...
start "" /MIN "%EXE_PATH%"

REM Așteaptă puțin pentru a verifica dacă s-a lansat
timeout /t 2 /nobreak >NUL

REM Verifică dacă procesul rulează acum
tasklist /FI "IMAGENAME eq AlephMonitor-AutoLogin.exe" 2>NUL | find /I /N "AlephMonitor-AutoLogin.exe">NUL
if "%ERRORLEVEL%"=="0" (
    echo [SUCCESS] AlephMonitor-AutoLogin.exe a fost lansat cu succes!
) else (
    echo [WARNING] Executabilul nu pare sa ruleze. Verifica logs.
)

REM Ieșire fără a afișa mesaje (pentru Task Scheduler)
exit /b 0

