@echo off
setlocal
rem Read-only aggregate personal kit check. Python 3.11+ required.
rem All arguments are passed unchanged to the checked Python module.
rem No registry, PATH, service, network or vendor program changes.
set "PK_SCRIPT=%~dp0kit_doctor.py"
py -3 -I "%PK_SCRIPT%" %*
exit /b %errorlevel%
