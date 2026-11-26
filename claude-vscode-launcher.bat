@echo off
setlocal DisableDelayedExpansion
title Claude Code - automatic VS Code terminal
set "CLAUDE_LAUNCHER_FILE=%~f0"
powershell.exe -NoLogo -NoProfile -Command "$ErrorActionPreference='Stop'; $s=[IO.File]::ReadAllText($env:CLAUDE_LAUNCHER_FILE); $m='# POWERSHELL'+' PAYLOAD'; $i=$s.IndexOf($m); if($i -lt 0){throw 'Launcher payload missing'}; & ([scriptblock]::Create($s.Substring($i+$m.Length)))"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Launcher exited with error %RC%.
echo.
pause
exit /b %RC%
# POWERSHELL PAYLOAD
$ErrorActionPreference = 'Stop'
function ShellQuote([string]$s) {
    $q = [string][char]39
    $d = [string][char]34
    return $q + $s.Replace($q, $q+$d+$q+$d+$q) + $q
}
function Base64([string]$s) {
    return [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($s))
}
function FindCommand([string]$name) {
    return (Get-Command $name -ErrorAction SilentlyContinue | Select-Object -First 1)
}
Write-Host '=========================================='
Write-Host ' Claude Code - connect to your server'
Write-Host '=========================================='
do {
    $ip = (Read-Host 'Server IP or hostname').Trim()
    if ($ip -notmatch '^[A-Za-z0-9][A-Za-z0-9.-]*$') { Write-Host 'Enter an IPv4 address or hostname.' }
} until ($ip -match '^[A-Za-z0-9][A-Za-z0-9.-]*$')
do {
    $user = (Read-Host 'Server username').Trim()
    if ($user -notmatch '^[A-Za-z0-9_][A-Za-z0-9_.-]*$') { Write-Host 'Enter a valid Linux username.' }
} until ($user -match '^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
$target = "$user@$ip"
$ssh = FindCommand 'ssh.exe'
if (!$ssh) { throw 'Windows OpenSSH Client is missing. Install it from Windows Optional Features.' }
Write-Host ''
Write-Host '1 = Open remote VS Code and launch Claude automatically (default)'
Write-Host '2 = Run Claude in this terminal'
do { $mode = (Read-Host 'Choose [1/2]').Trim(); if (!$mode) { $mode = '1' } } until ($mode -in @('1','2'))
if ($mode -eq '1') {
    $code = FindCommand 'code.cmd'
    if (!$code) { $code = FindCommand 'code' }
    if (!$code) {
        $candidates = @("$env:LOCALAPPDATA\Programs\Microsoft VS Code\bin\code.cmd", "$env:ProgramFiles\Microsoft VS Code\bin\code.cmd")
        foreach ($candidate in $candidates) { if (Test-Path -LiteralPath $candidate) { $code = Get-Command $candidate; break } }
    }
    if (!$code) { throw 'VS Code CLI was not found. Install VS Code with Add to PATH enabled.' }
}
Write-Host ''
do {
    $folder = (Read-Host 'Remote folder (absolute Linux path; Enter = home)').Trim()
    if ($folder -and !$folder.StartsWith('/')) { Write-Host 'Use an absolute path, for example /home/user/project.' }
} until (!$folder -or $folder.StartsWith('/'))
Write-Host ''
Write-Host '1 = Sonnet   2 = Opus   3 = Haiku   4 = Default   5 = Custom'
do { $choice = (Read-Host 'Model [1-5, Enter = 4]').Trim(); if (!$choice) { $choice = '4' } } until ($choice -in @('1','2','3','4','5'))
$model = switch ($choice) { '1' {'sonnet'} '2' {'opus'} '3' {'haiku'} '5' {
    do { $custom = (Read-Host 'Model name').Trim() } until ($custom -match '^[A-Za-z0-9][A-Za-z0-9_.:-]*$')
    $custom
} default { '' } }
$resume = (Read-Host 'Continue last Claude conversation in this folder? [y/N]').Trim()
$flags = ''
if ($model) { $flags += ' --model ' + (ShellQuote $model) }
if ($resume -eq 'y') { $flags += ' --continue' }
$launch = @'
export PATH="$HOME/.local/bin:$HOME/.npm-global/bin:$PATH"
if ! command -v claude >/dev/null 2>&1; then
    echo 'Claude Code CLI was not found on this server.'
    echo 'Ask the server administrator to install Claude Code or fix its PATH.'
    echo 'Alternatively, install the Claude Code extension in the remote VS Code window.'
    exit 127
fi
printf '\n=== CLAUDE AUTHENTICATION ===\n'
printf 'If sign-in is required, the authorized account owner must complete it.\n'
printf 'Open the displayed login URL in a local browser if needed.\n'
printf 'If Claude displays a code-entry prompt, follow its instructions.\n'
printf 'For an existing session, use /login only if you need to change accounts.\n\n'
'@
$launch += "`nexec claude$flags"
$launch = $launch -replace "`r`n", "`n"
# Prefer interactive authentication; OpenSSH reads the password itself.
$sshOptions = @('-o','ConnectTimeout=15','-o','PreferredAuthentications=keyboard-interactive,password,publickey')
Write-Host ''
Write-Host '=== SSH AUTHENTICATION ===' -ForegroundColor Cyan
Write-Host "Connecting to $target. Type your server password when SSH asks."
Write-Host 'Password characters are hidden. No password is saved or copied.'
Write-Host 'For a new host, verify its fingerprint with the administrator before accepting.'
if ($mode -eq '2') {
    $cd = if ($folder) { 'cd -- ' + (ShellQuote $folder) } else { 'cd ~' }
    # Encode multiline command for Windows native argument handling.
    $encoded = Base64 ($cd + " || exit 1`n" + $launch)
    # Use a script file descriptor, retaining the SSH terminal for Claude input.
    $remote = 'bash -lc ' + (ShellQuote ('source <(printf %s ' + $encoded + ' | base64 -d)'))
    & $ssh.Source @sshOptions '-t' $target $remote
    if ($LASTEXITCODE -ne 0) { throw "SSH/Claude ended with exit code $LASTEXITCODE." }
    return
}
# A separate remote workspace avoids overwriting any project .vscode files.
$workspaceFolder = if ($folder) { $folder } else { '../..' }
$hash = [Guid]::NewGuid().ToString('N')
$workspace = [ordered]@{
    folders = @(@{path=$workspaceFolder})
    extensions = @{recommendations=@('anthropic.claude-code')}
    tasks = @{
        version='2.0.0'
        tasks=@(@{
            label='Launch Claude Code'
            type='process'
            command='/bin/bash'
            args=@('-lc',$launch)
            options=@{cwd='${workspaceFolder}'}
            problemMatcher=@()
            runOptions=@{runOn='default'}
            presentation=@{reveal='always'; focus=$true; panel='dedicated'; clear=$false}
        })
    }
}
$json = $workspace | ConvertTo-Json -Depth 15
$payload = Base64 $json
$remoteScript = @'
set -eu
umask 077
'@
if ($folder) { $remoteScript += "`nif ! test -d " + (ShellQuote $folder) + "; then echo 'Remote folder does not exist.' >&2; exit 2; fi" }
$remoteScript += @'

mkdir -p "$HOME/.cache/claude-vscode-launcher"
'@
$remoteScript += "`nworkspace=`"`$HOME/.cache/claude-vscode-launcher/claude-$hash.code-workspace`"`n"
$remoteScript += "printf %s $payload | base64 -d > `"`$workspace`"`n"
$remoteScript += "printf %s " + (Base64 $launch) + " | base64 -d > `"`${workspace%.code-workspace}.sh`"`n"
$remoteScript += 'printf "CLAUDE_WORKSPACE=%s\n" "$workspace"'
$remoteScript = $remoteScript -replace "`r`n", "`n"
$remote = 'printf %s ' + (Base64 $remoteScript) + ' | base64 -d | bash'
# SSH prints its own password/host-key prompts to the console.
$result = & $ssh.Source @sshOptions $target $remote
if ($LASTEXITCODE -ne 0) { throw 'SSH authentication or remote workspace setup failed. Check the server address, username, password and folder.' }
$line = $result | Where-Object { $_ -like 'CLAUDE_WORKSPACE=*' } | Select-Object -Last 1
if (!$line) { throw 'The server did not return a workspace path.' }
$workspacePath = $line.Substring('CLAUDE_WORKSPACE='.Length).Trim()
if (!$workspacePath.StartsWith('/')) { throw 'Invalid remote workspace path.' }
Write-Host 'SSH login successful.' -ForegroundColor Green
Write-Host 'Checking VS Code Remote - SSH extension...'
$installed = & $code.Source --list-extensions
if ($LASTEXITCODE -ne 0) { throw 'Could not query VS Code extensions.' }
if ($installed -notcontains 'ms-vscode-remote.remote-ssh') {
    & $code.Source --install-extension ms-vscode-remote.remote-ssh
    if ($LASTEXITCODE -ne 0) { throw 'Remote - SSH extension installation failed.' }
}
Write-Host 'Checking the local Claude terminal launcher extension...'
$launcherId = 'local-archimedes.archimedes-claude-launcher'
$installed = & $code.Source --list-extensions
if ($installed -notcontains $launcherId) {
    $vsix = Join-Path ([IO.Path]::GetTempPath()) ('archimedes-claude-' + [Guid]::NewGuid().ToString('N') + '.vsix')
    try {
        [IO.File]::WriteAllBytes($vsix, [Convert]::FromBase64String('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'))
        & $code.Source --install-extension $vsix
        if ($LASTEXITCODE -ne 0) { Write-Warning 'Launcher extension install failed. The manual Launch Claude Code task is still available.' }
    } finally { Remove-Item -LiteralPath $vsix -ErrorAction SilentlyContinue }
}
Write-Host ''
Write-Host '=== AUTHENTICATE IN VS CODE ===' -ForegroundColor Cyan
Write-Host '1. Enter the SSH password again if VS Code asks.'
Write-Host '2. Trust the workspace only if you trust the server and folder.'
Write-Host '3. The local launcher opens the Claude Code integrated terminal automatically.'
Write-Host '4. If Claude requests login, the authorized account owner must approve it.'
Write-Host 'If Claude does not start: Ctrl+Shift+P > Archimedes: Open Claude Terminal.'
Write-Host 'Fallback: Ctrl+Shift+P > Tasks: Run Task > Launch Claude Code.'
Write-Host 'If SSH login is hidden: enable remote.SSH.showLoginTerminal in VS Code settings.'
Write-Host 'For the graphical panel: install the recommended Claude Code extension in SSH.'
# Use a remote file URI for the generated .code-workspace file.
$segments = $workspacePath.Split('/') | ForEach-Object { [Uri]::EscapeDataString($_) }
$encodedPath = $segments -join '/'
$uri = 'vscode-remote://ssh-remote+' + [Uri]::EscapeDataString($target) + $encodedPath
& $code.Source --new-window --file-uri $uri
if ($LASTEXITCODE -ne 0) { throw 'VS Code could not open the remote workspace.' }
Write-Host 'VS Code launch requested. Complete any prompts in the new window.' -ForegroundColor Green
