# KOINOS — resource-sharing prototype

This branch extends the Windows Claude Code launcher with a reusable workspace and a local resource dashboard. It shares authorized compute, not named-user Claude subscriptions. It is not a production multi-user broker.

## 1. One-time workspace setup
Run the original claude-vscode-launcher.bat once. The launcher now remembers the last generated remote workspace URI in %LOCALAPPDATA%/OpenShare-CLI/last-workspace.txt. Use open-last-workspace.bat next time. It retains the previously selected model and fresh/continue setting. Use the original setup again to change them. For password-free reconnections, configure individual SSH keys with ssh-agent and verify the host fingerprint with your administrator. VS Code may still prompt for trust or authentication when needed. No password or Claude token is saved by these scripts.

## 2. Check Claude analytics before expanding the project
Ask an organization administrator whether you use Claude Console API, Enterprise, Team or individual subscriptions. For Console API usage, obtain an authorized Admin key; for Enterprise, ask the primary owner for a read:analytics key. Set ANTHROPIC_ADMIN_KEY or ANTHROPIC_ANALYTICS_KEY in the local environment via an approved secret manager. Never place keys in Git or a browser.

From the repository root:
```powershell
python koinos/check_analytics.py console
# OR
python koinos/check_analytics.py enterprise
```
The probe reports HTTP status and first-page row count only. It does not expose user activity or prove a remaining quota API exists. HTTP 401/403 suggests checking authorization; a 200 response with no rows is not proof of idle capacity. See https://platform.claude.com/docs/en/manage-claude/analytics-api and https://support.claude.com/en/articles/12004354-purchase-and-manage-seats-on-team-plans.

## 3. Try the local dashboard
Python 3.10+ and OpenSSH are required. Remote Linux needs python3. No package installation is needed.
```powershell
cd koinos
python dashboard.py --demo
```
Open http://127.0.0.1:8765. Demo metrics are synthetic and Connect is disabled. Stop with Ctrl+C.
For actual metrics, copy resources.example.json to resources.local.json, edit names and SSH aliases, and configure each alias in your own SSH config. Use an authorized named Linux identity per employee, not somebody else's account. Test ssh -o BatchMode=yes -o StrictHostKeyChecking=yes dev-pool true once before using the dashboard. With your key and host trust in place, run python dashboard.py. On Windows, Connect SSH CLI opens an SSH terminal using the selected local alias; run Claude using your own authorized identity. Refresh samples to measure CPU and RAM. Unknown hosts remain unknown rather than idle. Low load is not proof of availability; there is no reservation or concurrency enforcement.

## 4. Production architecture (not implemented)
- Private HTTPS frontend with company SSO and role-based access, showing server names and timestamped metrics, no IPs or secrets.
- Admin enrollment of company-owned resources with stable private DNS or static IPs; individual SSH keys or short-lived SSH certificates; verify known hosts.
- Read-only agents for CPU, RAM, GPU utilization and heartbeat; stale data is unknown. Separate provider-approved organization analytics for Claude activity and spend.
- Transactional reservation service with TTL, owner priority, release and audit logs; only eligible machines can be allocated; enforce quotas at the server.
- Use organization-managed API access or individual named subscriptions in isolated per-user workspaces. Do not rotate through other users' Claude sessions.
- Backend retains inventory metadata, not employee passwords. Hashing a password is unsuitable for later SSH authentication; prefer per-user SSH keys or certificates. Secrets, when necessary, belong in an approved vault.
- Pilot with one authorized machine and two users. Verify reconnect, revocation, reservation race conditions, resource protection and billing before expanding.

## Test status
This branch is an implementation prototype. Real Windows, SSH and Anthropic API tests require the organization's machines, plan and keys. The demo is not real telemetry. Do not expose the localhost prototype to the network.

## 5. Historical Claude Code analytics (Console organizations)
Run `python koinos/usage_report.py` from the repository root after securely configuring the authorized `ANTHROPIC_ADMIN_KEY`. It reads all pages for one UTC date and aggregates sessions, input/output tokens and estimated cost by actor. Add `--date YYYY-MM-DD` to select another day. For the local admin-workstation dashboard, run `python dashboard.py --analytics` from `koinos/` with your private inventory configured. The analytics page contains user identifiers: do not expose the localhost server, and use this mode only on a restricted administrator workstation with organizational approval. The Enterprise path remains an access probe, not a fully integrated report. No report establishes remaining personal subscription quota, real-time activity or eligibility to use another account. The dashboard shows a UTC sampling timestamp for compute metrics.
