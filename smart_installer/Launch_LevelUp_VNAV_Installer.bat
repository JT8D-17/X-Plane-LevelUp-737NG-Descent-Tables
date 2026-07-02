@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -c "import tkinter" >nul 2>nul
  if %errorlevel%==0 (
    py -3 LevelUpVNAVInstaller.pyw
    goto :eof
  )
)
where python >nul 2>nul
if %errorlevel%==0 (
  python -c "import tkinter" >nul 2>nul
  if %errorlevel%==0 (
    python LevelUpVNAVInstaller.pyw
    goto :eof
  )
)
echo Python 3 with Tkinter is required.
echo Install Python from https://www.python.org/downloads/ and run this launcher again.
pause
