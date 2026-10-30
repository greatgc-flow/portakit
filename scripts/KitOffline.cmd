@echo off
setlocal
rem Offline personal kit readiness, no install/download/network.
rem Requires pre-approved Windows Python 3.11+.
rem Examples:
rem   KitOffline.cmd check --kit MyKit.json --root D:\Portable
rem   KitOffline.cmd check --kit MyKit.json --root D:\Portable --archive-dir D:\OriginalArchives
rem   KitOffline.cmd check --kit MyKit.json --root D:\Portable --archive-dir D:\OriginalArchives --skip-pending --out MyKit.check.json
rem Actual deployment is a separate explicit MyToolkit.cmd build --yes step.
python -I "%~dp0offline_assets.py" %*
exit /b %ERRORLEVEL%
