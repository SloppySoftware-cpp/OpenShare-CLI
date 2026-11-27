@echo off
setlocal DisableDelayedExpansion
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; $p=Join-Path $env:LOCALAPPDATA 'OpenShare-CLI\last-workspace.txt'; if(!(Test-Path -LiteralPath $p)){throw 'Run claude-vscode-launcher.bat first.'}; $u=(Get-Content -LiteralPath $p -Raw).Trim(); if($u -notmatch '^vscode-remote://ssh-remote\+[A-Za-z0-9._%\-]+/.+\.code-workspace$' -or $u -match '[\r\n]'){throw 'Invalid saved workspace. Run setup again.'}; $c=Get-Command code.cmd -ErrorAction SilentlyContinue; if(!$c){$c=Get-Command code -ErrorAction SilentlyContinue}; if(!$c){throw 'VS Code CLI is not on PATH.'}; & $c.Source --new-window --file-uri $u; exit $LASTEXITCODE"
if errorlevel 1 pause
exit /b %ERRORLEVEL%
