@echo off
setlocal
rem Explicit per-user classic Explorer context-menu integration, reversible.
rem Usage: ContextMenu.cmd install^|status^|remove notepad++^|winmerge [--root DIR]
python -I "%~dp0context_menu.py" %*
exit /b %ERRORLEVEL%
