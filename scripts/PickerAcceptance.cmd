@echo off
setlocal
rem PortaKit personal picker acceptance. Default: read-only prerequisites only.
rem Usage: PickerAcceptance.cmd
rem Guided operator checklist: PickerAcceptance.cmd --review --out D:\Evidence\PickerReview.json
rem Starts NO GUI/vendor binary; the operator manually opens MyToolkitGUI.cmd.
rem Result: 0=static check or all operator PASS, 1=FAIL/error, 2=SKIP/incomplete.
python -I "%~dp0picker_acceptance.py" %*
exit /b %ERRORLEVEL%
