@echo off
setlocal
rem One-click local Office 4 acceptance; optional PowerShell parameters are forwarded.
rem Requires Python 3.11+, supported Windows and licensed Office for actual COM comparisons.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Run-WinMerge-Office4.ps1" %*
exit /b %ERRORLEVEL%
