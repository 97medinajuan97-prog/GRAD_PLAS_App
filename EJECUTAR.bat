@echo off
setlocal EnableExtensions
title GRAD-PLAS - RAPITEST
cd /d "%~dp0"

set "PY="

where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"

if not defined PY (
    where python >nul 2>&1
    if not errorlevel 1 set "PY=python"
)

if not defined PY goto :nopython

%PY% "%~dp0main.py"
set "RC=%errorlevel%"
if not "%RC%"=="0" goto :error
goto :fin

:nopython
echo.
echo [ERROR] No se encontro Python en este equipo.
echo.
echo Instalalo desde:  https://www.python.org/downloads/
echo y marca la casilla "Add Python to PATH" durante la instalacion.
echo.
pause
exit /b 1

:error
echo.
echo [ERROR] La aplicacion se cerro con un error. Codigo: %RC%
echo.
pause

:fin
endlocal
