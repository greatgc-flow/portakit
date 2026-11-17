@echo off
setlocal DisableDelayedExpansion
rem Default data: sibling aegis-data. For another location run Aegis.Menu.ps1 -DataDirectory in PowerShell.
"%SystemRoot%\System32\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -File "%~dp0Aegis.Menu.ps1"
exit /b %ERRORLEVEL%
