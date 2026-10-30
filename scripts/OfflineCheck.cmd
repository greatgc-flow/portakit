@echo off
setlocal
rem Personal PortaKit offline preflight only: NO downloads/installs/system edits.
rem Usage: OfflineCheck.cmd --kit MyKit.json --root D:\PortableApps
rem Usage: OfflineCheck.cmd --kit MyKit.json --root D:\PortableApps --archive-dir D:\ApprovedArchives --skip-pending --out MyKit.ready.json
rem Result: 0=ready/no-op, 2=blocked/incomplete, 1=error.
python -I "%~dp0offline_ready.py" %*
exit /b %ERRORLEVEL%
