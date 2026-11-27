# Synergia CLI — utilization feasibility (2026-11-27)

## Decision
The meeting's first dependency is actual Claude subscription consumption, not Linux load. The documented Claude Code status-line JSON interface exposes five-hour and weekly utilization and reset times for supported subscriptions (the official documentation explicitly describes Pro/Max). It is event-driven, can omit fields before the first API response, and is not a continuously fresh or model-complete quota feed. Missing, expired or stale observations must be unknown, never zero.

Console admin API: delayed daily historical metrics, not remaining subscription quota. Enterprise analytics: separate primary-owner key; historical activity and eligible spend/usage data. Seat-based Enterprise cost and usage reports cover usage credits only. Team owners can use the official analytics UI. Confirm plan and permissions before choosing an adapter.

Anthropic's Claude Code compliance documentation requires individual end-user authentication and prohibits collecting or intermediating Claude credentials or session tokens. Do not rotate personal logins. Share company-owned compute via individual SSH identities; use approved organization-managed API capacity or spending arrangements for AI. Never collect employee SSH passwords; hashes cannot authenticate to SSH.

## One-account pilot
1. On the Linux host where the manager's own authorized Claude Code runs, clone this branch and run `python3 koinos/quota_probe.py --self-test` (synthetic only).
2. Run `claude --version` and confirm subscription with the interactive `/status` command. Back up existing status-line settings.
3. Merge the following field into the user's ~/.claude/settings.json; replace the path with the actual absolute path. Do not overwrite other settings or an existing status line without consent:
   `"statusLine": {"type": "command", "command": "python3 /absolute/path/Synergia-CLI/koinos/quota_probe.py"}`
4. Open Claude Code normally and send one ordinary prompt. Inspect the footer and run `python3 koinos/quota_probe.py --show` in another terminal. Compare the snapshot percentages and reset times against /usage or Settings > Usage. If fields are unavailable, report unknown.
5. The script retains only validated percentages, reset epochs and local observation time in ~/.synergia/quota-snapshot.json. No raw payload, prompts, credentials or paths retained. No network calls. No periodic refresh is configured; a local observation timestamp is not proof of fresh provider data. Restore original settings and delete the snapshot after the pilot.

## Go/no-go
- GO for local measurement if the results match the official usage display.
- GO for private, consent-based organizational reporting after verifying plan, access, data freshness and privacy controls.
- GO for shared compute with individual Linux identities, isolated workspaces, reservations and server-side enforcement. Stable private DNS can substitute for static IP.
- NO-GO for using another employee's personal Claude session, collecting credentials or treating low usage as available entitlement.
- No live account test has occurred; the organization plan, keys and host access are not available here. Synthetic test cases are included but must be executed.

## Official references
- https://code.claude.com/docs/en/statusline
- https://platform.claude.com/docs/en/manage-claude/claude-code-analytics-api
- https://platform.claude.com/docs/en/manage-claude/analytics-api
- https://support.claude.com/en/articles/12883420-view-usage-analytics-for-team-and-enterprise-plans
- https://code.claude.com/docs/en/legal-and-compliance
