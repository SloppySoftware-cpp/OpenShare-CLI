const vscode = require('vscode');
function quote(s) { return "'" + s.replace(/'/g, "'\\''") + "'"; }
function activate(context) {
  function launch() {
    const w = vscode.workspace.workspaceFile;
    if (vscode.env.remoteName !== 'ssh-remote' || !w || !vscode.workspace.isTrusted) return;
    if (!/\/\.cache\/claude-vscode-launcher\/claude-[a-f0-9]{32}\.code-workspace$/.test(w.path)) return;
    const existing = vscode.window.terminals.find(t => t.name === 'Claude Code');
    if (existing) { existing.show(false); return; }
    const folder = vscode.workspace.workspaceFolders?.[0];
    const terminal = vscode.window.createTerminal({name:'Claude Code', cwd:folder?.uri, shellPath:'/bin/bash', shellArgs:['-l']});
    terminal.show(false);
    terminal.sendText('bash ' + quote(w.path.replace(/\.code-workspace$/, '.sh')), true);
  }
  context.subscriptions.push(vscode.commands.registerCommand('archimedesLauncher.openClaude', launch));
  context.subscriptions.push(vscode.workspace.onDidGrantWorkspaceTrust(launch));
  launch();
}
exports.activate = activate;
