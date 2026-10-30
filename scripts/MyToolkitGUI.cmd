@echo off
setlocal
rem Optional GUI picker; does not install, remove, download or modify OS settings.
rem Requires standard Windows Python 3.11+ with optional Tkinter component.
rem If Tkinter is absent, use scripts\MyToolkit.cmd (fully supported CLI).
python -I "%~dp0toolkit_picker.py" %*
exit /b %ERRORLEVEL%
