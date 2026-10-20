@echo off
setlocal
rem Optional validated PortaKit category/profile selection and installation.
rem Usage: Toolsets.cmd list
rem Usage: Toolsets.cmd plan mes-support --include jq --exclude winmerge
rem Usage: Toolsets.cmd apply mes-support --yes [--recommended]
python -I "%~dp0toolsets.py" %*
exit /b %ERRORLEVEL%
