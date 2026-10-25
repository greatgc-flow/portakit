@echo off
setlocal
rem User-owned composable Portable Toolkit.
rem Examples:
rem   MyToolkit.cmd list --all
rem   MyToolkit.cmd create --name my-kit --tool jq --out my-kit.json
rem   MyToolkit.cmd plan --kit my-kit.json
rem   MyToolkit.cmd build --kit my-kit.json --offline-dir X:\ApprovedArchives --yes
rem All changes require build --yes; unverified selections block unless --skip-pending.
python -I "%~dp0my_toolkit.py" %*
exit /b %ERRORLEVEL%
