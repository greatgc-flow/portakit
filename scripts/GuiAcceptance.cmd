@echo off
setlocal
rem Safe default: read-only installed-GUI probe, local evidence only.
rem Manual review: GuiAcceptance.cmd --review --tools grepwin 7zip
rem Explicit launch (may have first-run effects): --review --launch
rem Everything launch requires --allow-everything-first-run as extra approval.
python -I "%~dp0gui_acceptance.py" %*
exit /b %ERRORLEVEL%
